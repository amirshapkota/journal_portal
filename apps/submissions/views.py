"""
ViewSets for Submission management.
Handles submission CRUD operations, author management, and document upload.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
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
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'abstract', 'submission_number']
    ordering_fields = ['title', 'created_at', 'submitted_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return SubmissionListSerializer
        elif self.action in ['update_status', 'submit', 'withdraw']:
            return SubmissionStatusUpdateSerializer
        return SubmissionSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        queryset = Submission.objects.select_related(
            'journal', 'corresponding_author__user'
        ).prefetch_related(
            'author_contributions__profile__user',
            'documents__current_version'
        )
        
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
    
    @extend_schema(
        summary="Submit for review",
        description="Submit a draft for review process.",
    )
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit manuscript for review."""
        submission = self.get_object()
        
        if submission.status != 'DRAFT':
            return Response(
                {'error': 'Only draft submissions can be submitted'},
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
        submission.status = 'SUBMITTED'
        submission.submitted_at = timezone.now()
        submission.save()
        
        # Generate submission number if not set
        if not submission.submission_number:
            submission.save()  # Triggers submission number generation
        
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
