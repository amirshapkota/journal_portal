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
        elif self.action in ['retrieve', 'my_requests']:
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
    
    def perform_update(self, serializer):
        """Update verification request and set status to PENDING for re-review."""
        verification_request = serializer.save()
        
        # When user updates their request, reset to PENDING for admin review
        # (unless it's already approved/rejected)
        if verification_request.status not in ['APPROVED', 'REJECTED', 'WITHDRAWN']:
            verification_request.status = 'PENDING'
            verification_request.additional_info_requested = ''  # Clear the info request
            verification_request.admin_notes = ''  # Clear admin notes
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
            
            # Add requested roles
            from apps.users.models import Role
            granted_roles = []
            
            for role_name in verification_request.requested_roles:
                if role_name == 'AUTHOR':
                    author_role, _ = Role.objects.get_or_create(name='AUTHOR')
                    profile.roles.add(author_role)
                    granted_roles.append('Author')
                elif role_name == 'REVIEWER':
                    reviewer_role, _ = Role.objects.get_or_create(name='REVIEWER')
                    profile.roles.add(reviewer_role)
                    granted_roles.append('Reviewer')
            
            profile.save()
            
            return Response({
                'detail': 'Verification approved',
                'profile_status': profile.verification_status,
                'roles_granted': granted_roles
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
        
        # Build response with score breakdown
        latest_request_data = None
        if latest_request:
            latest_request_data = {
                'id': str(latest_request.id),
                'status': latest_request.status,
                'requested_roles': latest_request.requested_roles,
                'auto_score': latest_request.auto_score,
                'score_breakdown': self._format_score_breakdown(latest_request),
                'created_at': latest_request.created_at.isoformat(),
            }
        
        return Response({
            'profile_status': profile.verification_status,
            'is_verified': profile.is_verified(),
            'has_pending_request': latest_request.status == 'PENDING' if latest_request else False,
            'latest_request': latest_request_data,
            'orcid_connected': hasattr(profile, 'orcid_integration') and profile.orcid_integration.status == 'CONNECTED',
            'roles': [role.name for role in profile.roles.all()]
        })
    
    def _format_score_breakdown(self, verification_request):
        """
        Format score details into a user-friendly array.
        
        Returns array of scoring factors with earned/max points.
        """
        score_details = verification_request.score_details or {}
        
        breakdown = [
            {
                'criterion': 'ORCID Verification',
                'description': 'Verified ORCID iD connected to account',
                'points_earned': score_details.get('orcid', 0),
                'points_possible': 30,
                'status': 'completed' if score_details.get('orcid', 0) > 0 else 'missing',
                'weight': 'highest'
            },
            {
                'criterion': 'Institutional Email',
                'description': 'Email from recognized academic domain (.edu, .ac.uk, etc.)',
                'points_earned': score_details.get('institutional_email', 0),
                'points_possible': 25,
                'status': 'completed' if score_details.get('institutional_email', 0) > 0 else 'missing',
                'weight': 'high'
            },
            {
                'criterion': 'Email-Affiliation Match',
                'description': 'Email domain matches claimed institution',
                'points_earned': score_details.get('email_affiliation_match', 0),
                'points_possible': 15,
                'status': 'completed' if score_details.get('email_affiliation_match', 0) > 0 else 'missing',
                'weight': 'medium'
            },
            {
                'criterion': 'Research Interests',
                'description': 'Detailed research interests provided (50+ characters)',
                'points_earned': score_details.get('research_interests', 0),
                'points_possible': 10,
                'status': 'completed' if score_details.get('research_interests', 0) > 0 else 'missing',
                'weight': 'low'
            },
            {
                'criterion': 'Academic Position',
                'description': 'Academic position/title specified',
                'points_earned': score_details.get('academic_position', 0),
                'points_possible': 10,
                'status': 'completed' if score_details.get('academic_position', 0) > 0 else 'missing',
                'weight': 'low'
            },
            {
                'criterion': 'Supporting Letter',
                'description': 'Letter from supervisor/institution (100+ characters)',
                'points_earned': score_details.get('supporting_letter', 0),
                'points_possible': 10,
                'status': 'completed' if score_details.get('supporting_letter', 0) > 0 else 'missing',
                'weight': 'low'
            }
        ]
        
        return breakdown
