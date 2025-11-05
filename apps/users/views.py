"""
Authentication and user management views.

Provides JWT-based authentication, user registration, profile management,
and comprehensive user account operations with email verification.
"""

from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.shortcuts import get_object_or_404
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import CustomUser, Profile, Role
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    ProfileSerializer,
    RoleSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    EmailVerificationSerializer
)
import logging

logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view with rate limiting and logging."""
    
    serializer_class = CustomTokenObtainPairSerializer
    
    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST'))
    def post(self, request, *args, **kwargs):
        """Handle login with rate limiting and set refresh token as HTTP-only cookie."""
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            logger.info(f"Successful login for user: {request.data.get('email')}")
            
            # Extract refresh token from response data
            refresh_token = response.data.get('refresh')
            if refresh_token:
                # Set refresh token as HTTP-only cookie
                response.set_cookie(
                    key='refresh_token',
                    value=refresh_token,
                    httponly=True,
                    secure=not settings.DEBUG,  # Use secure cookies in production
                    samesite='None' if not settings.DEBUG else 'Lax',  # 'None' for cross-origin in production
                    path='/',  # Make cookie available on all paths
                    max_age=7 * 24 * 60 * 60,  # 7 days (same as REFRESH_TOKEN_LIFETIME)
                )
                # Remove refresh token from response body for security
                response.data.pop('refresh', None)
        else:
            logger.warning(f"Failed login attempt for: {request.data.get('email')}")
        
        return response


class CustomTokenRefreshView(TokenRefreshView):
    """Custom token refresh view that reads refresh token from HTTP-only cookie."""
    
    @method_decorator(ratelimit(key='ip', rate='20/m', method='POST'))
    def post(self, request, *args, **kwargs):
        """Refresh access token using refresh token from cookie."""
        # Get refresh token from cookie
        refresh_token = request.COOKIES.get('refresh_token')
        
        # Debug logging
        logger.debug(f"Available cookies: {list(request.COOKIES.keys())}")
        
        if not refresh_token:
            logger.warning("Refresh token not found in cookies")
            return Response(
                {'detail': 'Refresh token not found in cookies.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Add refresh token to request data
        request.data['refresh'] = refresh_token
        
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            logger.info("Token refresh successful")
            # Since token rotation is disabled, refresh token stays the same
            # Just remove it from response body if present
            if 'refresh' in response.data:
                response.data.pop('refresh', None)
        else:
            logger.warning(f"Token refresh failed with status {response.status_code}")
        
        return response


class LogoutView(APIView):
    """Handle user logout by clearing the refresh token cookie."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Logout user",
        description="Logout user and clear refresh token cookie."
    )
    def post(self, request):
        """Clear refresh token cookie and blacklist the token."""
        try:
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception as e:
            logger.warning(f"Error blacklisting token during logout: {str(e)}")
        
        response = Response(
            {'detail': 'Successfully logged out.'},
            status=status.HTTP_200_OK
        )
        # Delete cookie with same attributes as when it was set
        response.delete_cookie(
            key='refresh_token',
            path='/',
            samesite='None' if not settings.DEBUG else 'Lax',
            secure=not settings.DEBUG  # Must match the secure flag used when setting
        )
        
        logger.info(f"User logged out: {request.user.email}")
        return response


@extend_schema_view(
    post=extend_schema(
        summary="Register new user",
        description="Create a new user account with email verification."
    )
)
class UserRegistrationView(generics.CreateAPIView):
    """Handle user registration with email verification."""
    
    queryset = CustomUser.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST'))
    def post(self, request, *args, **kwargs):
        """Register user and send verification email."""
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 201:
            user = CustomUser.objects.get(email=request.data.get('email'))
            self.send_verification_email(user)
            
            logger.info(f"New user registered: {user.email}")
            
            return Response({
                'message': 'Registration successful. Please check your email for verification.',
                'user_id': str(user.id)
            }, status=status.HTTP_201_CREATED)
        
        return response
    
    def send_verification_email(self, user):
        """Send email verification link using new EmailTemplate system."""
        from apps.notifications.tasks import send_email_verification_email
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}/"
        
        # Use new email system with Celery task and tracking
        # Call synchronously since Redis/Celery might not be running
        try:
            send_email_verification_email(str(user.id), verification_url)
        except Exception as exc:
            logger.error(f"Error queueing verification email: {exc}")
            # Fallback to direct send if Celery fails
            from django.core.mail import send_mail
            context = {
                'user': user,
                'verification_url': verification_url,
                'site_name': 'Journal Publication Portal'
            }
            subject = 'Verify your email address'
            message = render_to_string('emails/email_verification.txt', context)
            html_message = render_to_string('emails/email_verification.html', context)
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )


@extend_schema_view(
    post=extend_schema(
        summary="Verify email address",
        description="Verify user email with token from registration email."
    )
)
class EmailVerificationView(APIView):
    """Handle email verification."""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Verify email with token."""
        serializer = EmailVerificationSerializer(data=request.data)
        
        if serializer.is_valid():
            uid = request.data.get('uid')
            token = serializer.validated_data['token']
            
            try:
                user_id = force_str(urlsafe_base64_decode(uid))
                user = CustomUser.objects.get(pk=user_id)
                
                if default_token_generator.check_token(user, token):
                    user.is_verified = True
                    user.save()
                    
                    logger.info(f"Email verified for user: {user.email}")
                    
                    return Response({
                        'message': 'Email verification successful.'
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': 'Invalid or expired verification token.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
                return Response({
                    'error': 'Invalid verification link.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    post=extend_schema(
        summary="Change password",
        description="Change user password with current password verification."
    )
)
class PasswordChangeView(APIView):
    """Handle password change for authenticated users."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Change user password."""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Password changed for user: {request.user.email}")
            
            return Response({
                'message': 'Password changed successfully.'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    post=extend_schema(
        summary="Request password reset",
        description="Send password reset email to user."
    )
)
class PasswordResetRequestView(APIView):
    """Handle password reset requests."""
    
    permission_classes = [permissions.AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='3/m', method='POST'))
    def post(self, request):
        """Send password reset email."""
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                user = CustomUser.objects.get(email=email, is_active=True)
                self.send_reset_email(user)
            except CustomUser.DoesNotExist:
                pass  # Don't reveal if user exists
            
            return Response({
                'message': 'If an account exists with this email, a reset link has been sent.'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def send_reset_email(self, user):
        """Send password reset email using new EmailTemplate system."""
        from apps.notifications.tasks import send_password_reset_email
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
        
        # Use new email system with Celery task and tracking
        # Call synchronously since Redis/Celery might not be running
        try:
            send_password_reset_email(str(user.id), reset_url)
        except Exception as exc:
            logger.error(f"Error queueing password reset email: {exc}")
            # Fallback to direct send if Celery fails
            from django.core.mail import send_mail
            context = {
                'user': user,
                'reset_url': reset_url,
                'site_name': 'Journal Publication Portal'
            }
            subject = 'Password Reset Request'
            message = render_to_string('emails/password_reset.txt', context)
            html_message = render_to_string('emails/password_reset.html', context)
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )


@extend_schema_view(
    post=extend_schema(
        summary="Confirm password reset",
        description="Reset password with token from reset email."
    )
)
class PasswordResetConfirmView(APIView):
    """Handle password reset confirmation."""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Reset password with token."""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if serializer.is_valid():
            uid = request.data.get('uid')
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            try:
                user_id = force_str(urlsafe_base64_decode(uid))
                user = CustomUser.objects.get(pk=user_id)
                
                if default_token_generator.check_token(user, token):
                    user.set_password(new_password)
                    user.save()
                    
                    logger.info(f"Password reset completed for user: {user.email}")
                    
                    return Response({
                        'message': 'Password reset successful.'
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': 'Invalid or expired reset token.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
                return Response({
                    'error': 'Invalid reset link.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(summary="List users", description="Get paginated list of users."),
    retrieve=extend_schema(summary="Get user", description="Get specific user details."),
    update=extend_schema(summary="Update user", description="Update user information."),
    partial_update=extend_schema(summary="Partially update user", description="Partially update user information."),
    destroy=extend_schema(summary="Delete user", description="Delete a user account."),
)
class UserViewSet(ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    """
    ViewSet for user management.
    
    Provides read, update, and delete operations for existing users.
    User creation is only available through the registration endpoint.
    Note: POST method is completely removed - no user creation through this endpoint.
    """
    
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter users based on permissions."""
        user = self.request.user
        
        # Users can only see their own data unless they have admin privileges
        if user.is_staff or user.is_superuser:
            return CustomUser.objects.all()
        else:
            return CustomUser.objects.filter(id=user.id)


@extend_schema_view(
    list=extend_schema(summary="List profiles", description="Get paginated list of user profiles."),
    retrieve=extend_schema(summary="Get profile", description="Get specific user profile."),
    update=extend_schema(summary="Update profile", description="Update user profile."),
    partial_update=extend_schema(summary="Partially update profile", description="Partially update user profile."),
    destroy=extend_schema(summary="Delete profile", description="Delete a user profile."),
)
class ProfileViewSet(ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    """
    ViewSet for user profile management.
    
    Provides read, update, and delete operations for user profiles.
    Profile creation is automatic when users register - no manual creation allowed.
    """
    
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter profiles based on permissions."""
        user = self.request.user
        
        # Users can only see their own profile unless they have admin privileges
        if user.is_staff or user.is_superuser:
            return Profile.objects.all()
        else:
            return Profile.objects.filter(user=user)


@extend_schema_view(
    list=extend_schema(summary="List roles", description="Get available user roles."),
    retrieve=extend_schema(summary="Get role", description="Get specific role details."),
)
class RoleViewSet(ModelViewSet):
    """ViewSet for role management."""
    
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get']  # Read-only for now


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    """Get current authenticated user information."""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Health check endpoint."""
    return Response({
        'status': 'healthy',
        'service': 'journal-portal-api',
        'version': '1.0.0'
    })
