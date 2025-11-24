"""
Views for review management.
Handles review assignments, submissions, and reviewer recommendations.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from apps.reviews.models import (
    ReviewAssignment, Review, ReviewerRecommendation,
    EditorialDecision, RevisionRound, DecisionLetterTemplate
)
from apps.reviews.serializers import (
    ReviewAssignmentSerializer,
    ReviewAssignmentCreateSerializer,
    ReviewSerializer,
    ReviewCreateSerializer,
    ReviewerRecommendationSerializer,
    ReviewerExpertiseSerializer,
    ReviewInvitationAcceptSerializer,
    ReviewStatisticsSerializer,
    # Phase 4.3 serializers
    DecisionLetterTemplateSerializer,
    EditorialDecisionListSerializer,
    EditorialDecisionDetailSerializer,
    EditorialDecisionCreateSerializer,
    RevisionRoundListSerializer,
    RevisionRoundDetailSerializer,
    RevisionRoundCreateSerializer,
    RevisionSubmissionSerializer,
)
from apps.users.models import Profile
from apps.submissions.models import Submission
import logging

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="List review assignments",
        description="List all review assignments with filtering options"
    ),
    retrieve=extend_schema(
        summary="Get review assignment details",
        description="Get detailed information about a specific review assignment"
    ),
    create=extend_schema(
        summary="Create review assignment",
        description="Assign a reviewer to a submission"
    ),
)
class ReviewAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing review assignments.
    
    Endpoints:
    - GET /api/v1/reviews/assignments/ - List assignments
    - POST /api/v1/reviews/assignments/ - Create assignment
    - GET /api/v1/reviews/assignments/{id}/ - Get assignment details
    - GET /api/v1/reviews/assignments/my_assignments/ - Get user's assignments
    - GET /api/v1/reviews/assignments/pending/ - Get pending assignments
    - POST /api/v1/reviews/assignments/{id}/accept/ - Accept invitation
    - POST /api/v1/reviews/assignments/{id}/decline/ - Decline invitation
    - POST /api/v1/reviews/assignments/{id}/cancel/ - Cancel assignment
    """
    queryset = ReviewAssignment.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return ReviewAssignmentCreateSerializer
        return ReviewAssignmentSerializer
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        user = self.request.user
        
        # Admins and editors can see all assignments
        if user.is_staff or hasattr(user.profile, 'editor_journals'):
            return ReviewAssignment.objects.all().select_related(
                'submission', 'reviewer', 'assigned_by'
            )
        
        # Reviewers see their own assignments
        return ReviewAssignment.objects.filter(
            reviewer=user.profile
        ).select_related('submission', 'reviewer', 'assigned_by')
    
    def perform_create(self, serializer):
        """Create review assignment with automatic email notification."""
        assignment = serializer.save()
        
        # TODO: Send review invitation email
        logger.info(f"Review assignment created: {assignment.id}")
    
    @action(detail=False, methods=['get'])
    def my_assignments(self, request):
        """Get current user's review assignments."""
        assignments = ReviewAssignment.objects.filter(
            reviewer=request.user.profile
        ).select_related('submission', 'assigned_by').order_by('-invited_at')
        
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending review assignments for current user."""
        assignments = ReviewAssignment.objects.filter(
            reviewer=request.user.profile,
            status='PENDING'
        ).select_related('submission', 'assigned_by').order_by('due_date')
        
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def accepted(self, request):
        """Get accepted review assignments for current user."""
        assignments = ReviewAssignment.objects.filter(
            reviewer=request.user.profile,
            status='ACCEPTED'
        ).select_related('submission', 'assigned_by').order_by('due_date')
        
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Get completed review assignments for current user."""
        assignments = ReviewAssignment.objects.filter(
            reviewer=request.user.profile,
            status='COMPLETED'
        ).select_related('submission', 'assigned_by').order_by('-completed_at')
        
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def declined(self, request):
        """Get declined review assignments for current user."""
        assignments = ReviewAssignment.objects.filter(
            reviewer=request.user.profile,
            status='DECLINED'
        ).select_related('submission', 'assigned_by').order_by('-declined_at')
        
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept a review invitation."""
        assignment = self.get_object()
        
        if assignment.reviewer.user != request.user:
            return Response(
                {'detail': 'You can only accept your own review assignments.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if assignment.status != 'PENDING':
            return Response(
                {'detail': 'This assignment is not in pending status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignment.status = 'ACCEPTED'
        assignment.accepted_at = timezone.now()
        assignment.save()
        
        # TODO: Send acceptance confirmation email
        logger.info(f"Review assignment accepted: {assignment.id}")
        
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Decline a review invitation."""
        assignment = self.get_object()
        serializer = ReviewInvitationAcceptSerializer(data={'accept': False, **request.data})
        serializer.is_valid(raise_exception=True)
        
        if assignment.reviewer.user != request.user:
            return Response(
                {'detail': 'You can only decline your own review assignments.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if assignment.status != 'PENDING':
            return Response(
                {'detail': 'This assignment is not in pending status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignment.status = 'DECLINED'
        assignment.declined_at = timezone.now()
        assignment.decline_reason = serializer.validated_data.get('decline_reason', '')
        assignment.save()
        
        # TODO: Send decline notification email to editor
        logger.info(f"Review assignment declined: {assignment.id}")
        
        return Response(self.get_serializer(assignment).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a review assignment (editor only)."""
        assignment = self.get_object()
        
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only editors can cancel assignments.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if assignment.status == 'COMPLETED':
            return Response(
                {'detail': 'Cannot cancel completed assignments.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignment.status = 'CANCELLED'
        assignment.save()
        
        # TODO: Send cancellation notification email
        logger.info(f"Review assignment cancelled: {assignment.id}")
        
        return Response(self.get_serializer(assignment).data)


@extend_schema_view(
    list=extend_schema(
        summary="List reviews",
        description="List all submitted reviews with filtering options"
    ),
    retrieve=extend_schema(
        summary="Get review details",
        description="Get detailed information about a specific review"
    ),
    create=extend_schema(
        summary="Submit review",
        description="Submit a review for an assigned submission"
    ),
)
class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reviews.
    
    Endpoints:
    - GET /api/v1/reviews/ - List reviews
    - POST /api/v1/reviews/ - Submit review
    - GET /api/v1/reviews/{id}/ - Get review details
    - GET /api/v1/reviews/my_reviews/ - Get user's submitted reviews
    - GET /api/v1/reviews/submission_reviews/ - Get reviews for a submission
    """
    queryset = Review.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']  # No update/delete
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        user = self.request.user
        
        # Admins and editors can see all reviews
        if user.is_staff:
            return Review.objects.all().select_related(
                'submission', 'reviewer', 'assignment'
            )
        
        # Reviewers see their own reviews
        # Authors can see reviews for their submissions (if published)
        return Review.objects.filter(
            Q(reviewer=user.profile) |
            Q(submission__corresponding_author=user.profile, is_published=True)
        ).select_related('submission', 'reviewer', 'assignment')
    
    def perform_create(self, serializer):
        """Create review and update assignment status."""
        review = serializer.save()
        
        # TODO: Send review submission confirmation email
        # TODO: Notify editor of new review
        logger.info(f"Review submitted: {review.id}")
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Get current user's submitted reviews."""
        reviews = Review.objects.filter(
            reviewer=request.user.profile
        ).select_related('submission', 'assignment').order_by('-submitted_at')
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='submission_id',
                type=str,
                location=OpenApiParameter.QUERY,
                description='UUID of the submission',
                required=True
            )
        ]
    )
    def submission_reviews(self, request):
        """Get all reviews for a specific submission."""
        submission_id = request.query_params.get('submission_id')
        
        if not submission_id:
            return Response(
                {'detail': 'submission_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submission = get_object_or_404(Submission, id=submission_id)
        
        # Check permission to view reviews
        user = request.user
        can_view = (
            user.is_staff or
            submission.corresponding_author.user == user or
            ReviewAssignment.objects.filter(
                submission=submission,
                reviewer=user.profile
            ).exists()
        )
        
        if not can_view:
            return Response(
                {'detail': 'You do not have permission to view these reviews.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reviews = Review.objects.filter(
            submission=submission
        ).select_related('reviewer', 'assignment').order_by('-submitted_at')
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get version history for a review."""
        from apps.reviews.serializers import ReviewVersionSerializer
        review = self.get_object()
        
        versions = review.versions.all().order_by('-version_number')
        serializer = ReviewVersionSerializer(versions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def upload_attachment(self, request, pk=None):
        """Upload file attachment to a review."""
        from apps.reviews.models import ReviewAttachment
        review = self.get_object()
        
        # Verify user is the reviewer
        if review.reviewer != request.user.profile:
            return Response(
                {'detail': 'Only the reviewer can upload attachments.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get uploaded file
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'detail': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file type
        import os
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        allowed = ['.pdf', '.doc', '.docx', '.txt']
        if ext not in allowed:
            return Response(
                {'detail': f'File type {ext} not allowed. Allowed: {", ".join(allowed)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (10MB max)
        max_size = 10 * 1024 * 1024
        if uploaded_file.size > max_size:
            return Response(
                {'detail': f'File too large ({uploaded_file.size / 1024 / 1024:.2f}MB). Max: 10MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create attachment
        attachment = ReviewAttachment.objects.create(
            review=review,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            mime_type=uploaded_file.content_type,
            description=request.data.get('description', ''),
            uploaded_by=request.user.profile
        )
        
        from apps.reviews.serializers import ReviewAttachmentSerializer
        serializer = ReviewAttachmentSerializer(attachment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(
        summary="List reviewer recommendations",
        description="List ML-generated reviewer recommendations for submissions"
    ),
    retrieve=extend_schema(
        summary="Get recommendation details",
        description="Get detailed information about a specific reviewer recommendation"
    ),
)
class ReviewerRecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for reviewer recommendations (ML-generated).
    
    Endpoints:
    - GET /api/v1/reviews/recommendations/ - List recommendations
    - GET /api/v1/reviews/recommendations/{id}/ - Get recommendation details
    - GET /api/v1/reviews/recommendations/for_submission/ - Get recommendations for submission
    """
    queryset = ReviewerRecommendation.objects.all()
    serializer_class = ReviewerRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        user = self.request.user
        
        # Only editors and admins can see recommendations
        if not user.is_staff:
            return ReviewerRecommendation.objects.none()
        
        return ReviewerRecommendation.objects.all().select_related(
            'submission', 'recommended_reviewer'
        )
    
    @action(detail=False, methods=['get'])
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='submission_id',
                type=str,
                location=OpenApiParameter.QUERY,
                description='UUID of the submission',
                required=True
            ),
            OpenApiParameter(
                name='limit',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Maximum number of recommendations',
                required=False
            )
        ]
    )
    def for_submission(self, request):
        """Get reviewer recommendations for a specific submission."""
        submission_id = request.query_params.get('submission_id')
        limit = int(request.query_params.get('limit', 10))
        
        if not submission_id:
            return Response(
                {'detail': 'submission_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        recommendations = ReviewerRecommendation.objects.filter(
            submission_id=submission_id
        ).select_related('recommended_reviewer').order_by('-confidence_score')[:limit]
        
        serializer = self.get_serializer(recommendations, many=True)
        return Response(serializer.data)


@extend_schema_view(
    post=extend_schema(
        summary="Search for reviewers",
        description="Search for suitable reviewers based on expertise and availability"
    )
)
class ReviewerSearchViewSet(viewsets.ViewSet):
    """
    ViewSet for searching reviewers by expertise.
    
    Endpoints:
    - POST /api/v1/reviews/search_reviewers/ - Search reviewers
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """Search for reviewers by expertise keywords."""
        serializer = ReviewerExpertiseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        keywords = serializer.validated_data['keywords']
        min_score = serializer.validated_data['min_verification_score']
        exclude_ids = serializer.validated_data.get('exclude_reviewer_ids', [])
        limit = serializer.validated_data['limit']
        
        # Build query for expertise matching
        # Note: expertise_areas is a ManyToMany field to Concept model
        query = Q()
        for keyword in keywords:
            # Search in bio (TextField) and expertise_areas Concept names
            query |= Q(bio__icontains=keyword) | Q(expertise_areas__name__icontains=keyword)
        
        # Find reviewers
        reviewers = Profile.objects.filter(
            query,
            verification_status='GENUINE'
        ).exclude(
            id__in=exclude_ids
        ).distinct()  # Use distinct() because ManyToMany can create duplicates
        
        # Filter by verification score if available
        # TODO: Add verification score to query when VerificationRequest is linked
        
        reviewers = reviewers.select_related('user')[:limit]
        
        from apps.reviews.serializers import ReviewerProfileSerializer
        serializer = ReviewerProfileSerializer(reviewers, many=True)
        return Response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        summary="Get review statistics",
        description="Get comprehensive statistics about reviews and assignments"
    )
)
class ReviewStatisticsViewSet(viewsets.ViewSet):
    """
    ViewSet for review statistics and analytics.
    
    Endpoints:
    - GET /api/v1/reviews/statistics/ - Get global statistics
    - GET /api/v1/reviews/statistics/reviewer/ - Get reviewer-specific statistics
    - GET /api/v1/reviews/statistics/submission/ - Get submission-specific statistics
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get overview statistics for reviews."""
        assignments = ReviewAssignment.objects.all()
        reviews = Review.objects.all()
        
        stats = {
            'total_assignments': assignments.count(),
            'pending_assignments': assignments.filter(status='PENDING').count(),
            'accepted_assignments': assignments.filter(status='ACCEPTED').count(),
            'completed_reviews': reviews.count(),
            'declined_assignments': assignments.filter(status='DECLINED').count(),
            'overdue_reviews': assignments.filter(
                status__in=['PENDING', 'ACCEPTED'],
                due_date__lt=timezone.now()
            ).count(),
            'average_review_time_days': reviews.aggregate(
                avg_days=Avg(F('submitted_at') - F('assigned_at'))
            )['avg_days'].days if reviews.exists() else 0,
            'recommendations_breakdown': dict(
                reviews.values_list('recommendation').annotate(count=Count('id'))
            ),
            'reviewer_performance': {}  # TODO: Calculate reviewer performance metrics
        }
        
        serializer = ReviewStatisticsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def reviewer(self, request):
        """Get statistics for current reviewer."""
        reviewer = request.user.profile
        
        assignments = ReviewAssignment.objects.filter(reviewer=reviewer)
        reviews = Review.objects.filter(reviewer=reviewer)
        
        stats = {
            'total_assignments': assignments.count(),
            'accepted': assignments.filter(status='ACCEPTED').count(),
            'declined': assignments.filter(status='DECLINED').count(),
            'completed': reviews.count(),
            'pending': assignments.filter(status='PENDING').count(),
            'overdue': assignments.filter(
                status__in=['PENDING', 'ACCEPTED'],
                due_date__lt=timezone.now()
            ).count(),
            'average_review_time': reviews.aggregate(
                avg_days=Avg(F('submitted_at') - F('assigned_at'))
            ),
            'recommendations_given': dict(
                reviews.values_list('recommendation').annotate(count=Count('id'))
            )
        }
        
        return Response(stats)


@extend_schema_view(
    list=extend_schema(
        summary="List review form templates",
        description="Get all available review form templates"
    ),
    retrieve=extend_schema(
        summary="Get review form template",
        description="Get details of a specific review form template"
    ),
)
class ReviewFormTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for review form templates (read-only).
    
    Endpoints:
    - GET /api/v1/reviews/forms/ - List all form templates
    - GET /api/v1/reviews/forms/{id}/ - Get template details
    """
    from apps.reviews.models import ReviewFormTemplate
    from apps.reviews.serializers import ReviewFormTemplateSerializer
    
    queryset = ReviewFormTemplate.objects.filter(is_active=True)
    serializer_class = ReviewFormTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter templates based on journal if specified."""
        queryset = self.queryset
        journal_id = self.request.query_params.get('journal_id')
        
        if journal_id:
            # Get templates for specific journal or system-wide defaults
            queryset = queryset.filter(
                Q(journal_id=journal_id) | Q(journal__isnull=True)
            )
        
        return queryset.order_by('-is_default', 'name')


# ============================================================================
# PHASE 4.3: EDITORIAL DECISION MAKING VIEWSETS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List decision letter templates",
        description="Get all available decision letter templates"
    ),
    retrieve=extend_schema(
        summary="Get decision letter template",
        description="Get details of a specific decision letter template"
    ),
    create=extend_schema(
        summary="Create decision letter template",
        description="Create a new decision letter template (admin/editor only)"
    ),
)
class DecisionLetterTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for decision letter templates.
    
    Endpoints:
    - GET /api/v1/reviews/decision-templates/ - List templates
    - POST /api/v1/reviews/decision-templates/ - Create template (admin/editor)
    - GET /api/v1/reviews/decision-templates/{id}/ - Get template details
    - PATCH /api/v1/reviews/decision-templates/{id}/ - Update template (admin/editor)
    - DELETE /api/v1/reviews/decision-templates/{id}/ - Delete template (admin/editor)
    """
    from apps.reviews.models import DecisionLetterTemplate
    from apps.reviews.serializers import DecisionLetterTemplateSerializer
    
    queryset = DecisionLetterTemplate.objects.filter(is_active=True)
    serializer_class = DecisionLetterTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter templates based on journal if specified."""
        queryset = self.queryset
        journal_id = self.request.query_params.get('journal_id')
        decision_type = self.request.query_params.get('decision_type')
        
        if journal_id:
            # Get templates for specific journal or system-wide defaults
            queryset = queryset.filter(
                Q(journal_id=journal_id) | Q(journal__isnull=True)
            )
        
        if decision_type:
            queryset = queryset.filter(decision_type=decision_type)
        
        return queryset.order_by('-is_default', 'name')
    
    def perform_create(self, serializer):
        """Set created_by field."""
        serializer.save(created_by=self.request.user.profile)


@extend_schema_view(
    list=extend_schema(
        summary="List editorial decisions",
        description="List all editorial decisions with filtering options"
    ),
    retrieve=extend_schema(
        summary="Get editorial decision details",
        description="Get detailed information about a specific editorial decision"
    ),
    create=extend_schema(
        summary="Create editorial decision",
        description="Make an editorial decision on a submission (editor only)"
    ),
)
class EditorialDecisionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for editorial decisions.
    
    Endpoints:
    - GET /api/v1/reviews/decisions/ - List decisions
    - POST /api/v1/reviews/decisions/ - Create decision (editor only)
    - GET /api/v1/reviews/decisions/{id}/ - Get decision details
    - PATCH /api/v1/reviews/decisions/{id}/ - Update decision (editor only)
    - POST /api/v1/reviews/decisions/{id}/send_letter/ - Send decision letter to author
    - GET /api/v1/reviews/decisions/submission_decisions/ - Get decisions for a submission
    """
    from apps.reviews.models import EditorialDecision
    from apps.reviews.serializers import (
        EditorialDecisionListSerializer,
        EditorialDecisionDetailSerializer,
        EditorialDecisionCreateSerializer,
    )
    
    queryset = EditorialDecision.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']  # No delete
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return EditorialDecisionListSerializer
        elif self.action == 'create':
            return EditorialDecisionCreateSerializer
        return EditorialDecisionDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        user = self.request.user
        
        # Admins and editors can see all decisions
        if user.is_staff:
            return EditorialDecision.objects.all().select_related(
                'submission', 'decided_by', 'letter_template'
            )
        
        # Authors can see decisions for their submissions
        return EditorialDecision.objects.filter(
            submission__corresponding_author=user.profile
        ).select_related('submission', 'decided_by', 'letter_template')
    
    def perform_create(self, serializer):
        """Create editorial decision and trigger email notification."""
        from apps.notifications.tasks import send_decision_letter_email
        
        # Automatically set decided_by to current user's profile
        decision = serializer.save(decided_by=self.request.user.profile)
        
        # Update submission status based on editor's decision
        submission = decision.submission
        if decision.decision_type == 'ACCEPT':
            submission.status = 'ACCEPTED'
        elif decision.decision_type == 'REJECT':
            submission.status = 'REJECTED'
        elif decision.decision_type in ['MINOR_REVISION', 'MAJOR_REVISION']:
            submission.status = 'REVISION_REQUIRED'
        submission.save()
        
        # Send decision letter email to author
        try:
            send_decision_letter_email.delay(str(decision.id))
        except Exception as e:
            logger.warning(f"Failed to queue decision letter email: {e}")
        
        logger.info(f"Editorial decision created: {decision.id}")
    
    @action(detail=True, methods=['post'])
    def send_letter(self, request, pk=None):
        """Send decision letter to author via email."""
        from apps.notifications.tasks import send_decision_letter_email
        
        decision = self.get_object()
        
        if decision.notification_sent:
            return Response(
                {'detail': 'Decision letter already sent.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Send email via Celery task
        try:
            send_decision_letter_email.delay(str(decision.id))
            decision.notification_sent = True
            decision.notification_sent_at = timezone.now()
            decision.save()
        except Exception as e:
            logger.error(f"Failed to send decision letter: {e}")
            return Response(
                {'detail': 'Failed to send decision letter. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        logger.info(f"Decision letter sent for decision: {decision.id}")
        
        return Response({
            'detail': 'Decision letter sent successfully.',
            'sent_at': decision.notification_sent_at
        })
    
    @action(detail=False, methods=['get'])
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='submission_id',
                type=str,
                location=OpenApiParameter.QUERY,
                description='UUID of the submission',
                required=True
            )
        ]
    )
    def submission_decisions(self, request):
        """Get all editorial decisions for a specific submission."""
        submission_id = request.query_params.get('submission_id')
        
        if not submission_id:
            return Response(
                {'detail': 'submission_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submission = get_object_or_404(Submission, id=submission_id)
        
        # Check permission to view decisions
        user = request.user
        can_view = (
            user.is_staff or
            submission.corresponding_author.user == user
        )
        
        if not can_view:
            return Response(
                {'detail': 'You do not have permission to view these decisions.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        decisions = EditorialDecision.objects.filter(
            submission=submission
        ).select_related('decided_by', 'letter_template').order_by('-decision_date')
        
        serializer = EditorialDecisionListSerializer(decisions, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List revision rounds",
        description="List all revision rounds with filtering options"
    ),
    retrieve=extend_schema(
        summary="Get revision round details",
        description="Get detailed information about a specific revision round"
    ),
    create=extend_schema(
        summary="Create revision round",
        description="Create a revision round for a submission (editor only)"
    ),
)
class RevisionRoundViewSet(viewsets.ModelViewSet):
    """
    ViewSet for revision rounds.
    
    Endpoints:
    - GET /api/v1/reviews/revisions/ - List revision rounds
    - POST /api/v1/reviews/revisions/ - Create revision round (editor only)
    - GET /api/v1/reviews/revisions/{id}/ - Get revision round details
    - PATCH /api/v1/reviews/revisions/{id}/ - Update revision round
    - POST /api/v1/reviews/revisions/{id}/submit/ - Submit revised manuscript (author)
    - POST /api/v1/reviews/revisions/{id}/approve/ - Approve revision (editor)
    - POST /api/v1/reviews/revisions/{id}/reject/ - Reject revision (editor)
    - GET /api/v1/reviews/revisions/my_revisions/ - Get author's revision rounds
    """
    from apps.reviews.models import RevisionRound
    from apps.reviews.serializers import (
        RevisionRoundListSerializer,
        RevisionRoundDetailSerializer,
        RevisionRoundCreateSerializer,
        RevisionSubmissionSerializer,
    )
    from apps.submissions.models import Document
    
    queryset = RevisionRound.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']  # No delete
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return RevisionRoundListSerializer
        elif self.action == 'create':
            return RevisionRoundCreateSerializer
        elif self.action == 'submit':
            return RevisionSubmissionSerializer
        return RevisionRoundDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        user = self.request.user
        
        # Admins and editors can see all revision rounds
        if user.is_staff:
            return RevisionRound.objects.all().select_related(
                'submission', 'editorial_decision', 'revised_manuscript', 'response_letter'
            ).prefetch_related('reassigned_reviewers')
        
        # Authors can see revision rounds for their submissions
        return RevisionRound.objects.filter(
            submission__corresponding_author=user.profile
        ).select_related(
            'submission', 'editorial_decision', 'revised_manuscript', 'response_letter'
        ).prefetch_related('reassigned_reviewers')
    
    def perform_create(self, serializer):
        """Create revision round and send notification to author."""
        from apps.notifications.tasks import send_revision_request_email
        
        revision_round = serializer.save()
        
        # Update submission status
        revision_round.submission.status = 'REVISION_REQUIRED'
        revision_round.submission.save()
        
        # Send revision request email to author
        try:
            send_revision_request_email.delay(str(revision_round.id))
        except Exception as e:
            logger.warning(f"Failed to queue revision request email: {e}")
        
        logger.info(f"Revision round created: {revision_round.id}")
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit revised manuscript (author only)."""
        revision_round = self.get_object()
        
        # Check if user is the corresponding author
        if revision_round.submission.corresponding_author != request.user.profile:
            return Response(
                {'detail': 'Only the corresponding author can submit revisions.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if revision_round.status not in ['REQUESTED', 'IN_PROGRESS']:
            return Response(
                {'detail': 'This revision round is not accepting submissions.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate submission data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update revision round
        revision_round.status = 'SUBMITTED'
        revision_round.submitted_at = timezone.now()
        revision_round.revised_manuscript_id = serializer.validated_data['revised_manuscript_id']
        revision_round.response_letter_id = serializer.validated_data.get('response_letter_id')
        revision_round.author_notes = serializer.validated_data.get('author_notes', '')
        revision_round.save()
        
        # Update submission status
        revision_round.submission.status = 'REVISED'
        revision_round.submission.save()
        
        # Send revision submitted email to editor
        from apps.notifications.tasks import send_revision_submitted_notification
        try:
            send_revision_submitted_notification.delay(str(revision_round.id))
        except Exception as e:
            logger.warning(f"Failed to queue revision submitted notification: {e}")
        
        logger.info(f"Revision submitted for round: {revision_round.id}")
        
        detail_serializer = RevisionRoundDetailSerializer(revision_round)
        return Response(detail_serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve revised manuscript (editor only)."""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only editors can approve revisions.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        revision_round = self.get_object()
        
        if revision_round.status != 'SUBMITTED':
            return Response(
                {'detail': 'Only submitted revisions can be approved.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status
        revision_round.status = 'APPROVED'
        revision_round.save()
        
        # Update submission status
        revision_round.submission.status = 'UNDER_REVIEW'
        revision_round.submission.save()
        
        # Send approval notification to author
        from apps.notifications.tasks import send_revision_approved_email
        try:
            send_revision_approved_email.delay(str(revision_round.id))
        except Exception as e:
            logger.warning(f"Failed to queue revision approved email: {e}")
        
        logger.info(f"Revision approved for round: {revision_round.id}")
        
        serializer = self.get_serializer(revision_round)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject revised manuscript (editor only)."""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only editors can reject revisions.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        revision_round = self.get_object()
        
        if revision_round.status != 'SUBMITTED':
            return Response(
                {'detail': 'Only submitted revisions can be rejected.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status
        revision_round.status = 'REJECTED'
        revision_round.save()
        
        # Update submission status
        revision_round.submission.status = 'REJECTED'
        revision_round.submission.save()
        
        # Send rejection notification to author
        from apps.notifications.tasks import send_revision_rejected_email
        try:
            send_revision_rejected_email.delay(str(revision_round.id))
        except Exception as e:
            logger.warning(f"Failed to queue revision rejected email: {e}")
        
        logger.info(f"Revision rejected for round: {revision_round.id}")
        
        serializer = self.get_serializer(revision_round)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_revisions(self, request):
        """Get current author's revision rounds."""
        revisions = RevisionRound.objects.filter(
            submission__corresponding_author=request.user.profile
        ).select_related(
            'submission', 'editorial_decision'
        ).order_by('-requested_at')
        
        serializer = self.get_serializer(revisions, many=True)
        return Response(serializer.data)
