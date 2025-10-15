"""
Verification views for identity verification system.
Handles verification requests and admin review workflow.
"""
from django.utils import timezone
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action

from apps.users.models import VerificationRequest, Profile
from .verification_serializers import (
    VerificationRequestSerializer,
    VerificationRequestCreateSerializer,
    VerificationRequestDetailSerializer,
    VerificationReviewSerializer,
    VerificationResponseSerializer,
)


class VerificationRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for verification requests.
    Allows users to submit and manage their verification requests.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = VerificationRequestSerializer
    
    def get_queryset(self):
        """Return verification requests for the current user."""
        if self.request.user.is_staff:
            # Admins can see all requests
            return VerificationRequest.objects.all()
        # Regular users see only their own requests
        return VerificationRequest.objects.filter(profile=self.request.user.profile)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return VerificationRequestCreateSerializer
        elif self.action == 'retrieve':
            return VerificationRequestDetailSerializer
        return VerificationRequestSerializer
    
    def perform_create(self, serializer):
        """Create verification request and calculate auto score."""
        profile = self.request.user.profile
        
        # Check if user has ORCID connected
        orcid_verified = False
        orcid_id = ''
        try:
            orcid_integration = profile.orcid_integration
            if orcid_integration.status == 'CONNECTED':
                orcid_verified = True
                orcid_id = orcid_integration.orcid_id
        except:
            pass
        
        # Create the request
        verification_request = serializer.save(
            profile=profile,
            orcid_verified=orcid_verified,
            orcid_id=orcid_id
        )
        
        # Calculate automated score
        verification_request.calculate_auto_score()
        verification_request.save()
    
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Get all verification requests for current user."""
        requests = VerificationRequest.objects.filter(profile=request.user.profile)
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending verification requests for current user."""
        requests = VerificationRequest.objects.filter(
            profile=request.user.profile,
            status='PENDING'
        )
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """User responds to additional information request."""
        verification_request = self.get_object()
        
        if verification_request.status != 'INFO_REQUESTED':
            return Response(
                {'detail': 'Can only respond to info requested status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VerificationResponseSerializer(data=request.data)
        if serializer.is_valid():
            verification_request.user_response = serializer.validated_data['response']
            verification_request.user_response_at = timezone.now()
            verification_request.status = 'PENDING'
            verification_request.save()
            
            return Response({
                'detail': 'Response submitted successfully',
                'status': verification_request.status
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw verification request."""
        verification_request = self.get_object()
        
        if verification_request.status in ['APPROVED', 'REJECTED']:
            return Response(
                {'detail': 'Cannot withdraw approved or rejected requests'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        verification_request.status = 'WITHDRAWN'
        verification_request.save()
        
        return Response({'detail': 'Verification request withdrawn'})


class AdminVerificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin-only viewset for reviewing verification requests.
    """
    permission_classes = [IsAdminUser]
    serializer_class = VerificationRequestDetailSerializer
    queryset = VerificationRequest.objects.all()
    
    @action(detail=False, methods=['get'])
    def pending_review(self, request):
        """Get all pending verification requests."""
        requests = VerificationRequest.objects.filter(status='PENDING')
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def high_score(self, request):
        """Get pending requests with high auto scores (>70)."""
        requests = VerificationRequest.objects.filter(
            status='PENDING',
            auto_score__gte=70
        )
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a verification request."""
        verification_request = self.get_object()
        
        if verification_request.status not in ['PENDING', 'INFO_REQUESTED']:
            return Response(
                {'detail': 'Can only approve pending or info_requested requests'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VerificationReviewSerializer(data=request.data)
        if serializer.is_valid():
            # Update verification request
            verification_request.status = 'APPROVED'
            verification_request.reviewed_by = request.user
            verification_request.reviewed_at = timezone.now()
            verification_request.admin_notes = serializer.validated_data.get('admin_notes', '')
            verification_request.save()
            
            # Update profile verification status
            profile = verification_request.profile
            profile.verification_status = 'GENUINE'
            
            # Add requested role
            requested_role = verification_request.requested_role
            if requested_role == 'AUTHOR' or requested_role == 'BOTH':
                from apps.users.models import Role
                author_role, _ = Role.objects.get_or_create(name='Author')
                profile.roles.add(author_role)
            
            if requested_role == 'REVIEWER' or requested_role == 'BOTH':
                from apps.users.models import Role
                reviewer_role, _ = Role.objects.get_or_create(name='Reviewer')
                profile.roles.add(reviewer_role)
            
            profile.save()
            
            return Response({
                'detail': 'Verification approved',
                'profile_status': profile.verification_status,
                'roles_granted': requested_role
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a verification request."""
        verification_request = self.get_object()
        
        if verification_request.status not in ['PENDING', 'INFO_REQUESTED']:
            return Response(
                {'detail': 'Can only reject pending or info_requested requests'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VerificationReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        rejection_reason = serializer.validated_data.get('rejection_reason')
        if not rejection_reason:
            return Response(
                {'detail': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        verification_request.status = 'REJECTED'
        verification_request.reviewed_by = request.user
        verification_request.reviewed_at = timezone.now()
        verification_request.admin_notes = serializer.validated_data.get('admin_notes', '')
        verification_request.rejection_reason = rejection_reason
        verification_request.save()
        
        return Response({
            'detail': 'Verification rejected',
            'reason': rejection_reason
        })
    
    @action(detail=True, methods=['post'])
    def request_info(self, request, pk=None):
        """Request additional information from user."""
        verification_request = self.get_object()
        
        if verification_request.status != 'PENDING':
            return Response(
                {'detail': 'Can only request info for pending requests'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VerificationReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        additional_info = serializer.validated_data.get('additional_info_requested')
        if not additional_info:
            return Response(
                {'detail': 'Additional information request is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        verification_request.status = 'INFO_REQUESTED'
        verification_request.additional_info_requested = additional_info
        verification_request.admin_notes = serializer.validated_data.get('admin_notes', '')
        verification_request.save()
        
        return Response({
            'detail': 'Additional information requested',
            'info_requested': additional_info
        })


class VerificationStatusView(APIView):
    """
    Simple view to check current verification status.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get verification status for current user."""
        profile = request.user.profile
        
        # Get latest verification request
        latest_request = VerificationRequest.objects.filter(
            profile=profile
        ).order_by('-created_at').first()
        
        return Response({
            'profile_status': profile.verification_status,
            'is_verified': profile.is_verified(),
            'has_pending_request': latest_request.status == 'PENDING' if latest_request else False,
            'latest_request': {
                'id': str(latest_request.id),
                'status': latest_request.status,
                'requested_role': latest_request.requested_role,
                'auto_score': latest_request.auto_score,
                'created_at': latest_request.created_at.isoformat(),
            } if latest_request else None,
            'orcid_connected': hasattr(profile, 'orcid_integration') and profile.orcid_integration.status == 'CONNECTED',
            'roles': [role.name for role in profile.roles.all()]
        })
