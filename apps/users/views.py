"""
Authentication and user management views.

Provides JWT-based authentication, user registration, profile management,
and comprehensive user account operations with email verification.
"""

from rest_framework import status, permissions, generics, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import logout
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import transaction
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import CustomUser, Profile, Role, VerificationRequest
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
from apps.common.utils.activity_logger import log_activity
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
            # Try to get email from request data (could be 'email' or 'username')
            email = request.data.get('email') or request.data.get('username')
            logger.info(f"Successful login for user: {email}")
            
            # Log activity
            if email:
                try:
                    user = CustomUser.objects.get(email=email)
                    log_activity(
                        user=user,
                        action_type='LOGIN',
                        resource_type='USER',
                        resource_id=user.id,
                        metadata={'email': email, 'login_method': 'jwt'},
                        request=request
                    )
                except CustomUser.DoesNotExist:
                    logger.warning(f"Could not find user for logging: {email}")
            else:
                logger.warning("Could not extract email/username for logging")
            
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
            'refresh_token',
            path='/',
            samesite='None' if not settings.DEBUG else 'Lax'
        )
        
        logger.info(f"User logged out: {request.user.email}")
        
        # Log activity
        log_activity(
            user=request.user,
            action_type='LOGOUT',
            resource_type='USER',
            resource_id=request.user.id,
            metadata={'email': request.user.email, 'logout_method': 'jwt'},
            request=request
        )
        
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
            # Get the fresh user instance from database
            user = CustomUser.objects.get(email=request.data.get('email'))
            # Refresh from db to ensure we have the latest state
            user.refresh_from_db()
            
            logger.info(f"New user registered: {user.email}, last_login: {user.last_login}, email_verified: {user.email_verified}")
            
            self.send_verification_email(user)
            
            return Response({
                'message': 'Registration successful. Please check your email for verification.',
                'user_id': str(user.id)
            }, status=status.HTTP_201_CREATED)
        
        return response
    
    def send_verification_email(self, user):
        """Send email verification link using new EmailTemplate system."""
        from apps.notifications.tasks import send_email_verification_email
        
        # Refresh user from database to ensure latest state
        user.refresh_from_db()
        
        logger.info(f"Generating token for new registration - user: {user.email}, last_login: {user.last_login}, email_verified: {user.email_verified}, password hash: {user.password[:20]}...")
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        logger.info(f"Generated token for {user.email}: {token} (UID: {uid})")
        
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}/"
        
        logger.info(f"Full verification URL: {verification_url}")
        
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
    
    def post(self, request, uid=None, token=None):
        """Verify email with token from URL params or body."""
        # Accept uid and token from URL path or request body
        uid = uid or request.data.get('uid')
        token = token or request.data.get('token')
        
        logger.info(f"Email verification attempt - UID: {uid}, Token: {token[:20]}..." if token else "No token")
        
        if not uid or not token:
            return Response({
                'error': 'Both uid and token are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=user_id)
            
            logger.info(f"Verifying email for user: {user.email}, last_login: {user.last_login}, email_verified: {user.email_verified}")
            
            if user.email_verified:
                return Response({
                    'message': 'Email already verified.'
                }, status=status.HTTP_200_OK)
            
            # Check token validity
            is_valid = default_token_generator.check_token(user, token)
            logger.info(f"Token validation result for {user.email}: {is_valid}")
            
            if is_valid:
                user.email_verified = True
                user.save()
                
                logger.info(f"Email verified for user: {user.email}")
                
                return Response({
                    'message': 'Email verification successful.'
                }, status=status.HTTP_200_OK)
            else:
                logger.warning(f"Invalid verification token for user: {user.email}")
                return Response({
                    'error': 'Invalid or expired verification token.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist) as e:
            logger.error(f"Email verification error: {str(e)}")
            return Response({
                'error': 'Invalid verification link.'
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    post=extend_schema(
        summary="Resend verification email",
        description="Resend verification email to user's registered email address."
    )
)
class ResendVerificationEmailView(APIView):
    """Handle resending verification emails."""
    
    permission_classes = [permissions.AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='3/h', method='POST'))
    def post(self, request):
        """Resend verification email."""
        email = request.data.get('email')
        
        if not email:
            return Response({
                'error': 'Email address is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(email=email, is_active=True)
            
            if user.email_verified:
                return Response({
                    'message': 'Email is already verified.'
                }, status=status.HTTP_200_OK)
            
            # Send verification email
            self.send_verification_email(user)
            
            logger.info(f"Verification email resent to: {user.email}")
            
            return Response({
                'message': 'Verification email has been sent. Please check your inbox.'
            }, status=status.HTTP_200_OK)
            
        except CustomUser.DoesNotExist:
            # Don't reveal if user exists for security
            return Response({
                'message': 'If an account with this email exists and is not verified, a verification email has been sent.'
            }, status=status.HTTP_200_OK)
    
    def send_verification_email(self, user):
        """Send email verification link using new EmailTemplate system."""
        from apps.notifications.tasks import send_email_verification_email
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}/"
        
        # Use new email system with Celery task and tracking
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


@extend_schema(
    summary="Setup password for imported user",
    description="Allows imported OJS users to set their password for the first time using a token-based link",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'uid': {'type': 'string', 'description': 'Base64 encoded user ID'},
                'token': {'type': 'string', 'description': 'Password setup token'},
                'password': {'type': 'string', 'description': 'New password to set'}
            },
            'required': ['uid', 'token', 'password']
        }
    }
)
class PasswordSetupView(APIView):
    """Handle password setup for imported users."""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Set password for imported user with token."""
        uid = request.data.get('uid')
        token = request.data.get('token')
        password = request.data.get('password')
        
        if not all([uid, token, password]):
            return Response({
                'error': 'uid, token, and password are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=user_id)
            
            # Verify user is imported and doesn't have a usable password
            if not user.imported_from:
                return Response({
                    'error': 'This endpoint is only for imported users.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check token validity
            if default_token_generator.check_token(user, token):
                # Validate password strength (basic validation)
                if len(password) < 8:
                    return Response({
                        'error': 'Password must be at least 8 characters long.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Set the password
                user.set_password(password)
                user.email_verified = True  # Auto-verify email for imported users
                user.save()
                
                logger.info(f"Password setup completed for imported user: {user.email}")
                
                return Response({
                    'message': 'Password has been set successfully. You can now log in.'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid or expired setup token.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({
                'error': 'Invalid setup link.'
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Request password setup link for imported user",
    description="Sends a password setup link to an imported OJS user's email",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email', 'description': 'User email address'}
            },
            'required': ['email']
        }
    }
)
class PasswordSetupRequestView(APIView):
    """Request password setup link for imported users."""
    
    permission_classes = [permissions.AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='3/h', method='POST'))
    def post(self, request):
        """Send password setup link to imported user."""
        email = request.data.get('email')
        
        if not email:
            return Response({
                'error': 'Email is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(email=email, is_active=True)
            
            # Validate that user is imported from OJS
            if not user.imported_from:
                logger.warning(f"Password setup requested for non-imported user: {user.email}")
                # Don't reveal if user exists or not for security
                return Response({
                    'message': 'If an imported account exists with this email, a password setup link will be sent.'
                }, status=status.HTTP_200_OK)
            
            # Check if user already has a usable password
            if user.has_usable_password():
                logger.info(f"Password setup requested for user with existing password: {user.email}")
                # Don't reveal if user exists or not for security
                return Response({
                    'message': 'If an imported account exists with this email, a password setup link will be sent.'
                }, status=status.HTTP_200_OK)
            
            # Generate token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build setup URL
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            setup_url = f"{frontend_url}/setup-password/{uid}/{token}"
            
            # Send email
            subject = 'Set Up Your Password - Journal Portal'
            message = f"""
Hello {user.first_name or user.email},

Your account has been imported from OJS. To access the Journal Portal, you need to set up your password.

Click the link below to set your password:
{setup_url}

This link will expire in 24 hours.

If you did not request this, please ignore this email.

Best regards,
Journal Portal Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            logger.info(f"Password setup link sent to imported user: {user.email}")
            
        except CustomUser.DoesNotExist:
            logger.info(f"Password setup requested for non-existent email: {email}")
            # Don't reveal if user exists
            pass
        
        return Response({
            'message': 'If an imported account exists with this email, a password setup link will be sent.'
        }, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List users", description="Get paginated list of users."),
    retrieve=extend_schema(summary="Get user", description="Get specific user details."),
    update=extend_schema(summary="Update user", description="Update user information."),
    partial_update=extend_schema(summary="Partially update user", description="Partially update user information."),
    destroy=extend_schema(summary="Delete user", description="Delete a user account and all associated data."),
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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    filterset_fields = ['is_active', 'is_staff', 'profile__verification_status']
    ordering_fields = ['date_joined', 'last_login', 'username', 'email']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        """Filter users based on permissions."""
        user = self.request.user
        
        # Users can only see their own data unless they have admin privileges or are editors
        if user.is_staff or user.is_superuser:
            queryset = CustomUser.objects.all()
        # Check for EDITOR role
        elif hasattr(user, 'profile') and user.profile.roles.filter(name='EDITOR').exists():
            queryset = CustomUser.objects.all()
        else:
            queryset = CustomUser.objects.filter(id=user.id)
        
        # Filter by role query parameter if provided
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(profile__roles__name=role)
        
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete user and all associated data.
        This includes:
        - Profile and roles
        - Submissions (as corresponding author and co-author)
        - Documents created by user
        - Review assignments (as reviewer and assigner)
        - Reviews and decisions
        - Comments
        - Journal staff positions
        - Verification requests
        - Activity logs
        - ORCID integrations
        - All other related records
        
        Only superusers can delete users.
        """
        user = self.get_object()
        
        # Only superusers can delete users
        if not request.user.is_superuser:
            return Response(
                {'detail': 'Only superusers can delete user accounts.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Prevent self-deletion
        if user.id == request.user.id:
            return Response(
                {'detail': 'You cannot delete your own account.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get profile if exists
            profile = None
            if hasattr(user, 'profile'):
                profile = user.profile
            
            # Log what will be deleted
            deletion_summary = {
                'user': user.email,
                'deleted_items': {}
            }
            
            if profile:
                # Count items before deletion
                from apps.submissions.models import Submission, Document, AuthorContribution, Comment
                from apps.reviews.models import ReviewAssignment, Review, EditorialDecision
                from apps.journals.models import JournalStaff
                
                # Submissions where user is corresponding author
                corresponding_submissions = Submission.objects.filter(corresponding_author=profile).count()
                deletion_summary['deleted_items']['corresponding_submissions'] = corresponding_submissions
                
                # Author contributions (co-authored submissions)
                coauthor_contributions = AuthorContribution.objects.filter(profile=profile).count()
                deletion_summary['deleted_items']['author_contributions'] = coauthor_contributions
                
                # Documents created by user
                documents = Document.objects.filter(created_by=profile).count()
                deletion_summary['deleted_items']['documents'] = documents
                
                # Review assignments as reviewer
                review_assignments_as_reviewer = ReviewAssignment.objects.filter(reviewer=profile).count()
                deletion_summary['deleted_items']['review_assignments_as_reviewer'] = review_assignments_as_reviewer
                
                # Review assignments assigned by user
                review_assignments_assigned = ReviewAssignment.objects.filter(assigned_by=profile).count()
                deletion_summary['deleted_items']['review_assignments_assigned'] = review_assignments_assigned
                
                # Reviews
                reviews = Review.objects.filter(reviewer=profile).count()
                deletion_summary['deleted_items']['reviews'] = reviews
                
                # Editorial decisions
                decisions = EditorialDecision.objects.filter(decided_by=profile).count()
                deletion_summary['deleted_items']['editorial_decisions'] = decisions
                
                # Comments
                comments = Comment.objects.filter(author=profile).count()
                deletion_summary['deleted_items']['comments'] = comments
                
                # Journal staff positions
                staff_positions = JournalStaff.objects.filter(profile=profile).count()
                deletion_summary['deleted_items']['journal_staff_positions'] = staff_positions
                
                # Verification requests
                verification_requests = VerificationRequest.objects.filter(profile=profile).count()
                deletion_summary['deleted_items']['verification_requests'] = verification_requests
            
            # Verification requests reviewed by user
            reviewed_verifications = VerificationRequest.objects.filter(reviewed_by=user).count()
            deletion_summary['deleted_items']['reviewed_verifications'] = reviewed_verifications
            
            # Log the deletion attempt
            logger.info(f"Deleting user {user.email} (ID: {user.id}) by {request.user.email}")
            logger.info(f"Deletion summary: {deletion_summary}")
            
            # Perform deletion
            # Django's CASCADE will handle most relationships automatically
            # But we need to handle some special cases
            
            with transaction.atomic():
                if profile:
                    # Delete submissions where user is corresponding author
                    # This will cascade delete related documents, reviews, etc.
                    Submission.objects.filter(corresponding_author=profile).delete()
                    
                    # Remove author contributions (don't delete the submissions, just the contributions)
                    AuthorContribution.objects.filter(profile=profile).delete()
                    
                    # Delete review assignments where user is reviewer or assigner
                    ReviewAssignment.objects.filter(reviewer=profile).delete()
                    ReviewAssignment.objects.filter(assigned_by=profile).delete()
                    
                    # Delete reviews by user
                    Review.objects.filter(reviewer=profile).delete()
                    
                    # Delete editorial decisions by user
                    EditorialDecision.objects.filter(decided_by=profile).delete()
                    
                    # Delete comments by user
                    Comment.objects.filter(author=profile).delete()
                    
                    # Delete journal staff positions
                    JournalStaff.objects.filter(profile=profile).delete()
                    
                    # Delete verification requests
                    VerificationRequest.objects.filter(profile=profile).delete()
                
                # Set reviewed_by to NULL for verification requests reviewed by this user
                VerificationRequest.objects.filter(reviewed_by=user).update(reviewed_by=None)
                
                # Delete activity logs
                from apps.common.models import ActivityLog
                ActivityLog.objects.filter(user=user).delete()
                
                # Delete ORCID integration
                from apps.integrations.models import ORCIDIntegration
                if profile:
                    ORCIDIntegration.objects.filter(profile=profile).delete()
                
                # Finally delete the user (this will cascade delete the profile)
                user_email = user.email
                user.delete()
            
            logger.info(f"Successfully deleted user {user_email}")
            
            # Log activity for the admin who performed deletion
            log_activity(
                user=request.user,
                action_type='DELETE',
                resource_type='USER',
                resource_id=None,
                metadata={
                    'deleted_user': user_email,
                    'deletion_summary': deletion_summary
                },
                request=request
            )
            
            return Response(
                {
                    'detail': f'User {user_email} and all associated data have been deleted successfully.',
                    'deletion_summary': deletion_summary
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error deleting user {user.email}: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'detail': f'Error deleting user: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'affiliation', 'orcid_id', 'bio']
    filterset_fields = ['verification_status']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
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
