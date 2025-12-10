"""
ViewSets for Submission management.
Handles submission CRUD operations, author management, and document upload.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Submission, AuthorContribution, Document, DocumentVersion, Comment
from .serializers import (
    SubmissionSerializer, SubmissionListSerializer, SubmissionStatusUpdateSerializer,
    AuthorContributionSerializer, AddAuthorSerializer, DocumentSerializer,
    DocumentUploadSerializer, DocumentVersionSerializer, CommentSerializer
)
from apps.users.models import Profile


class SubmissionPermissions(permissions.BasePermission):
    """
    Custom permissions for submission management.
    - Authors can manage their own submissions
    - Journal staff can manage submissions to their journals
    - Admins can manage all submissions
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Admin can do anything
        if user.is_superuser or user.is_staff:
            return True
        
        # Author permissions
        if hasattr(user, 'profile'):
            # Corresponding author
            if obj.corresponding_author == user.profile:
                return True
            
            # Co-author
            if AuthorContribution.objects.filter(
                submission=obj,
                profile=user.profile
            ).exists():
                # Co-authors can view and comment, but not edit
                return request.method in permissions.SAFE_METHODS
            
            # Journal staff permissions
            from apps.journals.models import JournalStaff
            if JournalStaff.objects.filter(
                journal=obj.journal,
                profile=user.profile,
                is_active=True
            ).exists():
                return True
        
        return False


class SubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Submission management.
    
    Provides CRUD operations for submissions with author and document management.
    """
    queryset = Submission.objects.all()
    permission_classes = [SubmissionPermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'abstract', 'submission_number', 'corresponding_author__user__first_name', 'corresponding_author__user__last_name', 'corresponding_author__user__email']
    filterset_fields = ['status', 'journal']
    ordering_fields = ['title', 'created_at', 'submitted_at', 'updated_at', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return SubmissionListSerializer
        elif self.action in ['update_status', 'submit', 'withdraw']:
            return SubmissionStatusUpdateSerializer
        # Dynamically create a serializer that includes staff_members in journal
        from apps.journals.serializers import JournalSerializer, JournalStaffSerializer
        class SubmissionWithJournalStaffSerializer(SubmissionSerializer):
            journal = JournalSerializer(read_only=True)
        return SubmissionWithJournalStaffSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        queryset = Submission.objects.select_related(
            'journal', 'corresponding_author', 'corresponding_author__user',
            'section', 'category', 'category__section',
            'research_type', 'research_type__category',
            'area', 'area__research_type'
        ).prefetch_related(
            'author_contributions__profile__user',
            'documents',
            'review_assignments'
        )
        
        # Filter by journal if provided
        journal_id = self.request.query_params.get('journal')
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Admin sees all
        if user.is_superuser or user.is_staff:
            return queryset
        
        # Filter based on user's involvement
        if hasattr(user, 'profile'):
            # User's own submissions or co-authored submissions
            user_submissions = Q(corresponding_author=user.profile) | Q(
                author_contributions__profile=user.profile
            )
            
            # Submissions to journals where user is staff
            from apps.journals.models import JournalStaff
            staff_journals = JournalStaff.objects.filter(
                profile=user.profile,
                is_active=True
            ).values_list('journal_id', flat=True)
            
            journal_submissions = Q(journal_id__in=staff_journals)
            
            return queryset.filter(user_submissions | journal_submissions).distinct()
        
        return queryset.none()
    
    def perform_create(self, serializer):
        """
        Create submission. OJS sync must be triggered manually using sync-to-ojs endpoint.
        """
        submission = serializer.save()
    
    def perform_update(self, serializer):
        """
        Update submission. OJS sync must be triggered manually using sync-to-ojs endpoint.
        """
        submission = serializer.save()
    
    @extend_schema(
        summary="List draft submissions",
        description="Get submissions in DRAFT status. By default shows only your own submissions. Use ?view_as=editor to see all journal submissions.",
        parameters=[
            OpenApiParameter(
                name='view_as',
                description='Filter submissions by role: author (default, only your submissions) or editor (all journal submissions)',
                required=False,
                type=str
            )
        ],
        responses={200: SubmissionListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def drafts(self, request):
        """Get all draft submissions for the user."""
        queryset = self.get_queryset().filter(status='DRAFT')
        
        # Default to author view unless explicitly requesting editor view
        view_as = request.query_params.get('view_as', 'author').lower()
        if view_as == 'author' and hasattr(request.user, 'profile'):
            # Only show submissions where user is author (corresponding or co-author)
            queryset = queryset.filter(
                Q(corresponding_author=request.user.profile) |
                Q(author_contributions__profile=request.user.profile)
            ).distinct()
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SubmissionListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = SubmissionListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="List unassigned submissions",
        description="Get submissions that are SUBMITTED but have no reviewers assigned. By default shows only your own submissions. Use ?view_as=editor to see all journal submissions.",
        parameters=[
            OpenApiParameter(
                name='view_as',
                description='Filter submissions by role: author (default, only your submissions) or editor (all journal submissions)',
                required=False,
                type=str
            )
        ],
        responses={200: SubmissionListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def unassigned(self, request):
        """Get all unassigned submissions (no reviewers assigned)."""
        from django.db.models import Count
        
        queryset = self.get_queryset().filter(
            status__in=[
                'SUBMITTED'
            ]
        ).annotate(
            review_count=Count('review_assignments')
        ).filter(review_count=0)
        
        # Default to author view unless explicitly requesting editor view
        view_as = request.query_params.get('view_as', 'author').lower()
        if view_as == 'author' and hasattr(request.user, 'profile'):
            # Only show submissions where user is author (corresponding or co-author)
            queryset = queryset.filter(
                Q(corresponding_author=request.user.profile) |
                Q(author_contributions__profile=request.user.profile)
            ).distinct()
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SubmissionListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = SubmissionListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="List active submissions",
        description="Get submissions that are actively being reviewed (have reviewers assigned). By default shows only your own submissions. Use ?view_as=editor to see all journal submissions.",
        parameters=[
            OpenApiParameter(
                name='view_as',
                description='Filter submissions by role: author (default, only your submissions) or editor (all journal submissions)',
                required=False,
                type=str
            )
        ],
        responses={200: SubmissionListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active submissions (reviewers assigned and not yet published/archived)."""
        from django.db.models import Count
        
        queryset = self.get_queryset().filter(
            status__in=[
                'UNDER_REVIEW',
                'REVISION_REQUIRED', 'REVISION_REQUESTED', 'REVISED',
                'ACCEPTANCE_REQUESTED', 'REJECTION_REQUESTED', 'ACCEPTED', 'COPYEDITING',
            ]
        ).annotate(
            review_count=Count('review_assignments')
        ).filter(review_count__gt=0)
        
        # Default to author view unless explicitly requesting editor view
        view_as = request.query_params.get('view_as', 'author').lower()
        if view_as == 'author' and hasattr(request.user, 'profile'):
            # Only show submissions where user is author (corresponding or co-author)
            queryset = queryset.filter(
                Q(corresponding_author=request.user.profile) |
                Q(author_contributions__profile=request.user.profile)
            ).distinct()
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SubmissionListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = SubmissionListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="List archived submissions",
        description="Get submissions that are completed (ACCEPTED, REJECTED, WITHDRAWN, or PUBLISHED). By default shows only your own submissions. Use ?view_as=editor to see all journal submissions.",
        parameters=[
            OpenApiParameter(
                name='view_as',
                description='Filter submissions by role: author (default, only your submissions) or editor (all journal submissions)',
                required=False,
                type=str
            )
        ],
        responses={200: SubmissionListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def archived(self, request):
        """Get all archived submissions (completed)."""
        queryset = self.get_queryset().filter(
            status__in=[
                'REJECTED', 'WITHDRAWN', 'PUBLISHED', 
            ]
        )
        
        # Default to author view unless explicitly requesting editor view
        view_as = request.query_params.get('view_as', 'author').lower()
        if view_as == 'author' and hasattr(request.user, 'profile'):
            # Only show submissions where user is author (corresponding or co-author)
            queryset = queryset.filter(
                Q(corresponding_author=request.user.profile) |
                Q(author_contributions__profile=request.user.profile)
            ).distinct()
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SubmissionListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = SubmissionListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="Submit for review",
        description="Submit a draft for review process or resubmit after revisions.",
    )
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit manuscript for review."""
        submission = self.get_object()
        
        # Allow submission from DRAFT or REVISION_REQUIRED status
        if submission.status not in ['DRAFT', 'REVISION_REQUIRED']:
            return Response(
                {'error': 'Only draft or revision-required submissions can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if submission has required documents
        if not submission.documents.filter(document_type='MANUSCRIPT').exists():
            return Response(
                {'error': 'Manuscript document is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status and set submission timestamp
        from django.utils import timezone
        
        # If resubmitting after revision
        if submission.status == 'REVISION_REQUIRED':
            # Check if there are active reviewers (assignments in ACCEPTED status)
            has_active_reviewers = submission.review_assignments.filter(
                status__in=['PENDING', 'ACCEPTED']
            ).exists()
            
            # If reviewers are already assigned, set to UNDER_REVIEW
            # Otherwise, set to REVISED (waiting for editor to assign reviewers)
            submission.status = 'UNDER_REVIEW' if has_active_reviewers else 'REVISED'
        else:
            # First time submission
            submission.status = 'SUBMITTED'
            # Only set submitted_at for first-time submission
            if not submission.submitted_at:
                submission.submitted_at = timezone.now()
        
        submission.save()
        
        serializer = self.get_serializer(submission)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Withdraw submission",
        description="Withdraw a submission from review.",
    )
    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw submission."""
        submission = self.get_object()
        
        if submission.status in ['REJECTED', 'WITHDRAWN', 'PUBLISHED']:
            return Response(
                {'error': f'Cannot withdraw {submission.status.lower()} submission'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submission.status = 'WITHDRAWN'
        submission.save()
        
        serializer = self.get_serializer(submission)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Sync submission to OJS",
        description="Manually sync this submission to OJS. Creates a new submission in OJS if not already synced, or updates existing OJS submission.",
    )
    @action(detail=True, methods=['post'], url_path='sync-to-ojs')
    def sync_to_ojs(self, request, pk=None):
        """Manually sync submission to OJS."""
        submission = self.get_object()
        
        # Check if journal has OJS configured
        if not submission.journal.ojs_enabled:
            return Response(
                {'error': 'OJS is not enabled for this journal'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not submission.journal.ojs_api_url or not submission.journal.ojs_api_key:
            return Response(
                {'error': 'OJS is not configured for this journal'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.integrations.ojs_sync import sync_submission_to_ojs
            result = sync_submission_to_ojs(submission)
            
            if result['success']:
                return Response({
                    'detail': f'Submission successfully {result["action"]}d in OJS',
                    'ojs_id': result['ojs_id'],
                    'action': result['action']
                })
            else:
                return Response(
                    {'error': f'Failed to sync to OJS: {result.get("error", "Unknown error")}'},
                    status=status.HTTP_502_BAD_GATEWAY
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to sync submission {submission.id} to OJS: {str(e)}")
            return Response(
                {'error': f'Failed to sync to OJS: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Update submission status",
        description="Update submission status (for journal staff).",
        request=SubmissionStatusUpdateSerializer
    )
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update submission status."""
        submission = self.get_object()
        
        # Check permissions - only journal staff or admin
        user = request.user
        if not (user.is_staff or user.is_superuser):
            if hasattr(user, 'profile'):
                from apps.journals.models import JournalStaff
                is_staff = JournalStaff.objects.filter(
                    journal=submission.journal,
                    profile=user.profile,
                    is_active=True
                ).exists()
                if not is_staff:
                    return Response(
                        {'error': 'Only journal staff can update status'},
                        status=status.HTTP_403_FORBIDDEN
                    )
        
        serializer = SubmissionStatusUpdateSerializer(
            data=request.data,
            context={'submission': submission}
        )
        
        if serializer.is_valid():
            submission.status = serializer.validated_data['status']
            submission.save()
            
            response_serializer = self.get_serializer(submission)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="List submission authors",
        description="Get all authors for a submission.",
        responses={200: AuthorContributionSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def authors(self, request, pk=None):
        """Get submission authors."""
        submission = self.get_object()
        authors = submission.author_contributions.all().order_by('order')
        serializer = AuthorContributionSerializer(authors, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Add author",
        description="Add a co-author to the submission.",
        request=AddAuthorSerializer,
        responses={201: AuthorContributionSerializer}
    )
    @action(detail=True, methods=['post'])
    def add_author(self, request, pk=None):
        """Add co-author to submission."""
        submission = self.get_object()
        serializer = AddAuthorSerializer(
            data=request.data,
            context={'submission': submission}
        )
        
        if serializer.is_valid():
            profile = serializer.validated_data['profile_id']
            
            author_contrib = AuthorContribution.objects.create(
                submission=submission,
                profile=profile,
                contrib_role=serializer.validated_data['contrib_role'],
                order=serializer.validated_data['order'],
                contribution_details=serializer.validated_data.get('contribution_details', {})
            )
            
            response_serializer = AuthorContributionSerializer(author_contrib)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Remove author",
        description="Remove a co-author from the submission.",
        parameters=[
            OpenApiParameter(
                name='author_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Profile ID of the author to remove'
            )
        ]
    )
    @action(detail=True, methods=['delete'], url_path='authors/(?P<author_id>[^/.]+)')
    def remove_author(self, request, pk=None, author_id=None):
        """Remove co-author from submission."""
        submission = self.get_object()
        
        # Cannot remove corresponding author
        if str(submission.corresponding_author.id) == author_id:
            return Response(
                {'error': 'Cannot remove corresponding author'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        author_contrib = get_object_or_404(
            AuthorContribution,
            submission=submission,
            profile_id=author_id
        )
        
        author_contrib.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @extend_schema(
        summary="List submission documents",
        description="Get all documents for a submission.",
        responses={200: DocumentSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """Get submission documents."""
        submission = self.get_object()
        documents = submission.documents.all().order_by('-created_at')
        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="Upload document",
        description="Upload a document to the submission.",
        request=DocumentUploadSerializer,
        responses={201: DocumentSerializer}
    )
    @action(detail=True, methods=['post'])
    def upload_document(self, request, pk=None):
        """Upload document to submission."""
        submission = self.get_object()
        serializer = DocumentUploadSerializer(
            data=request.data,
            context={'submission': submission, 'request': request}
        )
        
        if serializer.is_valid():
            document = serializer.save()
            response_serializer = DocumentSerializer(document, context={'request': request})
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Get submission statistics",
        description="Get statistics for a submission."
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get submission statistics."""
        submission = self.get_object()
        
        stats = {
            'author_count': submission.author_contributions.count(),
            'document_count': submission.documents.count(),
            'total_versions': DocumentVersion.objects.filter(
                document__submission=submission
            ).count(),
            'comments_count': Comment.objects.filter(
                document_version__document__submission=submission
            ).count(),
            'unresolved_comments': Comment.objects.filter(
                document_version__document__submission=submission,
                resolved=False
            ).count(),
            'status_history': {
                'current_status': submission.status,
                'created_at': submission.created_at,
                'submitted_at': submission.submitted_at,
                'last_updated': submission.updated_at
            }
        }
        
        return Response(stats)
