"""
ViewSets for Copyediting and Production workflow management.
Handles copyediting assignments, files, discussions, production, and publication scheduling.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .copyediting_models import (
    CopyeditingAssignment, CopyeditingFile, CopyeditingDiscussion,
    CopyeditingMessage, CopyeditingMessageAttachment
)
from .production_models import (
    ProductionAssignment, ProductionFile, ProductionDiscussion,
    ProductionMessage, ProductionMessageAttachment, PublicationSchedule
)
from .workflow_serializers import (
    CopyeditingAssignmentSerializer, CopyeditingAssignmentListSerializer,
    CopyeditingFileSerializer, CopyeditingDiscussionSerializer,
    CopyeditingDiscussionListSerializer, CopyeditingMessageSerializer,
    ProductionAssignmentSerializer, ProductionAssignmentListSerializer,
    ProductionFileSerializer, ProductionDiscussionSerializer,
    ProductionDiscussionListSerializer, ProductionMessageSerializer,
    PublicationScheduleSerializer
)
from .models import Submission


class WorkflowPermissions(permissions.BasePermission):
    """
    Custom permissions for workflow management.
    - Editors and journal staff can manage workflow
    - Copyeditors/Production assistants can manage their assigned tasks
    - Authors can view their submission's workflow
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        import logging
        logger = logging.getLogger(__name__)
        
        user = request.user
        logger.info(f"Permission check for user: {user.email}, action: {view.action}, obj: {obj}")
        
        # Admin can do anything
        if user.is_superuser or user.is_staff:
            logger.info(f"Permission GRANTED: User is superuser/staff")
            return True
        
        if hasattr(user, 'profile'):
            logger.info(f"User has profile: {user.profile.id}")
            # Get submission based on object type
            submission = None
            if hasattr(obj, 'submission'):
                submission = obj.submission
            elif isinstance(obj, Submission):
                submission = obj
            
            if submission:
                logger.info(f"Submission found: {submission.id}, journal: {submission.journal.id}")
                
                # Author permissions (read-only)
                if submission.corresponding_author == user.profile:
                    result = request.method in permissions.SAFE_METHODS or view.action in ['add_message']
                    logger.info(f"Author check: {result}")
                    return result
                
                # Journal staff permissions
                from apps.journals.models import JournalStaff
                is_staff = JournalStaff.objects.filter(
                    journal=submission.journal,
                    profile=user.profile,
                    is_active=True
                ).exists()
                if is_staff:
                    logger.info(f"Permission GRANTED: User is journal staff")
                    return True
                
                # Copyeditor/Production assistant permissions
                if hasattr(obj, 'copyeditor') and obj.copyeditor == user.profile:
                    logger.info(f"Permission GRANTED: User is copyeditor")
                    return True
                if hasattr(obj, 'production_assistant') and obj.production_assistant == user.profile:
                    logger.info(f"Permission GRANTED: User is production assistant")
                    return True
                
                # Allow the assigner to manage the assignment
                if hasattr(obj, 'assigned_by') and obj.assigned_by == user.profile:
                    logger.info(f"Permission GRANTED: User is assigner (assigned_by)")
                    return True
                    
                logger.warning(f"Permission DENIED: No matching permission found")
            else:
                logger.warning(f"Permission DENIED: No submission found")
        else:
            logger.warning(f"Permission DENIED: User has no profile")
        
        return False
        
        return False


@extend_schema_view(
    list=extend_schema(
        summary="List copyediting assignments",
        description="Get paginated list of copyediting assignments filtered by submission, copyeditor, or status."
    ),
    retrieve=extend_schema(
        summary="Get copyediting assignment",
        description="Get detailed information about a specific copyediting assignment."
    ),
    create=extend_schema(
        summary="Create copyediting assignment",
        description="Assign a copyeditor to a submission. Moves submission to COPYEDITING status."
    ),
    update=extend_schema(
        summary="Update copyediting assignment",
        description="Update copyediting assignment details (status, instructions, etc.)."
    ),
    partial_update=extend_schema(
        summary="Partially update copyediting assignment",
        description="Partially update copyediting assignment fields."
    ),
)
class CopyeditingAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing copyediting assignments.
    
    Provides CRUD operations and actions for copyediting workflow management.
    """
    queryset = CopyeditingAssignment.objects.all()
    permission_classes = [WorkflowPermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['submission', 'copyeditor', 'status', 'assigned_by']
    search_fields = ['submission__title', 'copyeditor__user__email', 'copyeditor__user__first_name']
    ordering_fields = ['assigned_at', 'due_date', 'status']
    ordering = ['-assigned_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return CopyeditingAssignmentListSerializer
        return CopyeditingAssignmentSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        queryset = CopyeditingAssignment.objects.select_related(
            'submission', 'copyeditor__user', 'assigned_by__user'
        ).prefetch_related('files', 'discussions')
        
        # Admin sees all
        if user.is_superuser or user.is_staff:
            return queryset
        
        if hasattr(user, 'profile'):
            # Copyeditor sees their assignments
            if user.profile.roles.filter(name='COPY_EDITOR').exists():
                return queryset.filter(copyeditor=user.profile)
            
            # Editor sees assignments for their journals
            from apps.journals.models import JournalStaff
            staff_journals = JournalStaff.objects.filter(
                profile=user.profile,
                is_active=True
            ).values_list('journal_id', flat=True)
            
            # Authors see assignments for their submissions
            return queryset.filter(
                Q(submission__journal_id__in=staff_journals) |
                Q(submission__corresponding_author=user.profile)
            ).distinct()
        
        return queryset.none()
    
    @extend_schema(
        summary="Start copyediting",
        description="Mark copyediting assignment as IN_PROGRESS and create initial copyediting files from submission documents."
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start copyediting work and create initial files."""
        assignment = self.get_object()
        
        if assignment.status != 'PENDING':
            return Response(
                {'detail': 'Can only start pending assignments.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignment.status = 'IN_PROGRESS'
        assignment.save()
        
        # Create copyediting files from submission documents
        from django.core.files.base import ContentFile
        files_created = 0
        
        # Get submission documents (manuscripts and supplementary files)
        submission_docs = assignment.submission.documents.filter(
            document_type__in=['MANUSCRIPT', 'SUPPLEMENTARY', 'REVISED_MANUSCRIPT']
        )
        
        for doc in submission_docs:
            # Skip if copyediting file already exists for this document
            existing = CopyeditingFile.objects.filter(
                assignment=assignment,
                submission=assignment.submission,
                original_filename=doc.file_name
            ).exists()
            
            if existing:
                continue
            
            # Create copyediting file from document
            try:
                copyediting_file = CopyeditingFile.objects.create(
                    assignment=assignment,
                    submission=assignment.submission,
                    file_type='INITIAL_DRAFT',
                    description=f'Initial draft from submission document: {doc.title}',
                    uploaded_by=request.user.profile if hasattr(request.user, 'profile') else assignment.assigned_by,
                    original_filename=doc.file_name,
                    file_size=doc.file_size,
                    mime_type=doc.original_file.file.content_type if doc.original_file else 'application/octet-stream',
                    version=1
                )
                
                # Copy the file content
                if doc.original_file:
                    doc.original_file.file.seek(0)
                    file_content = doc.original_file.file.read()
                    copyediting_file.file.save(
                        doc.file_name,
                        ContentFile(file_content),
                        save=True
                    )
                    files_created += 1
            except Exception as e:
                # Log error but continue with other files
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating copyediting file from document {doc.id}: {str(e)}")
        
        serializer = self.get_serializer(assignment)
        return Response({
            **serializer.data,
            'files_created': files_created
        })
    
    @extend_schema(
        summary="Complete copyediting",
        description="Mark copyediting assignment as completed.",
        request={'application/json': {'type': 'object', 'properties': {
            'completion_notes': {'type': 'string', 'description': 'Notes about completion'}
        }}}
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete copyediting work."""
        assignment = self.get_object()
        
        if assignment.status not in ['PENDING', 'IN_PROGRESS']:
            return Response(
                {'detail': 'Can only complete pending or in-progress assignments.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignment.status = 'COMPLETED'
        assignment.completion_notes = request.data.get('completion_notes', '')
        assignment.save()
        
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get assignment files",
        description="List all files associated with this copyediting assignment."
    )
    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        """Get assignment files."""
        assignment = self.get_object()
        files = assignment.files.all().order_by('-created_at')
        serializer = CopyeditingFileSerializer(files, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get assignment discussions",
        description="List all discussions for this copyediting assignment."
    )
    @action(detail=True, methods=['get'])
    def discussions(self, request, pk=None):
        """Get assignment discussions."""
        assignment = self.get_object()
        discussions = assignment.discussions.all().order_by('-updated_at')
        serializer = CopyeditingDiscussionListSerializer(discussions, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get assignment participants",
        description="List all participants involved in this copyediting assignment."
    )
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Get all participants (copyeditor, editor, author)."""
        assignment = self.get_object()
        from apps.users.serializers import ProfileSerializer
        
        participants = [
            {**ProfileSerializer(assignment.copyeditor).data, 'role': 'copyeditor'},
            {**ProfileSerializer(assignment.assigned_by).data, 'role': 'assigned_by'},
            {**ProfileSerializer(assignment.submission.corresponding_author).data, 'role': 'author'},
        ]
        
        return Response(participants)


@extend_schema_view(
    list=extend_schema(
        summary="List copyediting files",
        description="Get paginated list of copyediting files filtered by assignment, submission, or file type."
    ),
    retrieve=extend_schema(
        summary="Get copyediting file",
        description="Get detailed information about a specific copyediting file."
    ),
    create=extend_schema(
        summary="Upload copyediting file",
        description="Upload a new copyediting file (draft or copyedited version)."
    ),
    update=extend_schema(
        summary="Update copyediting file",
        description="Update copyediting file metadata."
    ),
)
class CopyeditingFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing copyediting files.
    
    Handles upload, download, and management of copyediting files.
    """
    queryset = CopyeditingFile.objects.all()
    serializer_class = CopyeditingFileSerializer
    permission_classes = [WorkflowPermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['assignment', 'submission', 'file_type', 'is_approved']
    search_fields = ['original_filename', 'description']
    ordering_fields = ['created_at', 'version']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        queryset = CopyeditingFile.objects.select_related(
            'assignment__submission', 'uploaded_by__user', 'approved_by__user'
        )
        
        # Admin sees all
        if user.is_superuser or user.is_staff:
            return queryset
        
        if hasattr(user, 'profile'):
            # Filter based on assignments user has access to
            from apps.journals.models import JournalStaff
            staff_journals = JournalStaff.objects.filter(
                profile=user.profile,
                is_active=True
            ).values_list('journal_id', flat=True)
            
            return queryset.filter(
                Q(assignment__copyeditor=user.profile) |
                Q(submission__journal_id__in=staff_journals) |
                Q(submission__corresponding_author=user.profile)
            ).distinct()
        
        return queryset.none()
    
    @extend_schema(
        summary="Approve copyediting file",
        description="Approve a copyediting file for further processing."
    )
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve copyediting file."""
        file_obj = self.get_object()
        
        if file_obj.is_approved:
            return Response(
                {'detail': 'File is already approved.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        file_obj.is_approved = True
        file_obj.approved_by = request.user.profile if hasattr(request.user, 'profile') else None
        file_obj.approved_at = timezone.now()
        file_obj.save()
        
        serializer = self.get_serializer(file_obj)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List copyediting discussions",
        description="Get paginated list of copyediting discussions filtered by assignment, submission, or status."
    ),
    retrieve=extend_schema(
        summary="Get copyediting discussion",
        description="Get detailed information about a specific copyediting discussion with all messages."
    ),
    create=extend_schema(
        summary="Create copyediting discussion",
        description="Start a new copyediting discussion thread."
    ),
)
class CopyeditingDiscussionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing copyediting discussions.
    
    Handles discussion threads between copyeditor, author, and editor.
    """
    queryset = CopyeditingDiscussion.objects.all()
    permission_classes = [WorkflowPermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['assignment', 'submission', 'status', 'started_by']
    search_fields = ['subject']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    http_method_names = ['get', 'post', 'patch', 'delete']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return CopyeditingDiscussionListSerializer
        return CopyeditingDiscussionSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        queryset = CopyeditingDiscussion.objects.select_related(
            'assignment__submission', 'started_by__user', 'closed_by__user'
        ).prefetch_related('participants__user', 'messages__author__user')
        
        # Admin sees all
        if user.is_superuser or user.is_staff:
            return queryset
        
        if hasattr(user, 'profile'):
            # Filter discussions where user is participant or has access to submission
            from apps.journals.models import JournalStaff
            staff_journals = JournalStaff.objects.filter(
                profile=user.profile,
                is_active=True
            ).values_list('journal_id', flat=True)
            
            return queryset.filter(
                Q(participants=user.profile) |
                Q(submission__journal_id__in=staff_journals) |
                Q(submission__corresponding_author=user.profile)
            ).distinct()
        
        return queryset.none()
    
    @extend_schema(
        summary="Add message to discussion",
        description="Add a new message to this copyediting discussion thread.",
        request=CopyeditingMessageSerializer
    )
    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """Add message to discussion."""
        discussion = self.get_object()
        
        if discussion.status == 'CLOSED':
            return Response(
                {'detail': 'Cannot add messages to closed discussion.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CopyeditingMessageSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            message = serializer.save(discussion=discussion)
            
            # Add author as participant if not already
            if hasattr(request.user, 'profile'):
                discussion.participants.add(request.user.profile)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Close discussion",
        description="Close this copyediting discussion thread."
    )
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close discussion."""
        discussion = self.get_object()
        
        if discussion.status == 'CLOSED':
            return Response(
                {'detail': 'Discussion is already closed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        discussion.status = 'CLOSED'
        discussion.closed_by = request.user.profile if hasattr(request.user, 'profile') else None
        discussion.closed_at = timezone.now()
        discussion.save()
        
        serializer = self.get_serializer(discussion)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Reopen discussion",
        description="Reopen a closed copyediting discussion thread."
    )
    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """Reopen closed discussion."""
        discussion = self.get_object()
        
        if discussion.status == 'OPEN':
            return Response(
                {'detail': 'Discussion is already open.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        discussion.status = 'OPEN'
        discussion.closed_by = None
        discussion.closed_at = None
        discussion.save()
        
        serializer = self.get_serializer(discussion)
        return Response(serializer.data)


# ============= PRODUCTION VIEWSETS =============

@extend_schema_view(
    list=extend_schema(
        summary="List production assignments",
        description="Get paginated list of production assignments filtered by submission, production assistant, or status."
    ),
    retrieve=extend_schema(
        summary="Get production assignment",
        description="Get detailed information about a specific production assignment."
    ),
    create=extend_schema(
        summary="Create production assignment",
        description="Assign a production assistant to a submission. Moves submission to IN_PRODUCTION status."
    ),
    update=extend_schema(
        summary="Update production assignment",
        description="Update production assignment details (status, instructions, etc.)."
    ),
)
class ProductionAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing production assignments.
    
    Provides CRUD operations and actions for production workflow management.
    """
    queryset = ProductionAssignment.objects.all()
    permission_classes = [WorkflowPermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['submission', 'production_assistant', 'status', 'assigned_by']
    search_fields = ['submission__title', 'production_assistant__user__email']
    ordering_fields = ['assigned_at', 'due_date', 'status']
    ordering = ['-assigned_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ProductionAssignmentListSerializer
        return ProductionAssignmentSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        queryset = ProductionAssignment.objects.select_related(
            'submission', 'production_assistant__user', 'assigned_by__user'
        ).prefetch_related('files', 'discussions')
        
        # Admin sees all
        if user.is_superuser or user.is_staff:
            return queryset
        
        if hasattr(user, 'profile'):
            # Production assistant sees their assignments
            if user.profile.roles.filter(name__in=['LAYOUT_EDITOR', 'PRODUCTION_EDITOR']).exists():
                return queryset.filter(production_assistant=user.profile)
            
            # Editor sees assignments for their journals
            from apps.journals.models import JournalStaff
            staff_journals = JournalStaff.objects.filter(
                profile=user.profile,
                is_active=True
            ).values_list('journal_id', flat=True)
            
            # Authors see assignments for their submissions
            return queryset.filter(
                Q(submission__journal_id__in=staff_journals) |
                Q(submission__corresponding_author=user.profile)
            ).distinct()
        
        return queryset.none()
    
    @extend_schema(
        summary="Start production",
        description="Mark production assignment as IN_PROGRESS."
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start production work."""
        assignment = self.get_object()
        
        if assignment.status != 'PENDING':
            return Response(
                {'detail': 'Can only start pending assignments.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignment.status = 'IN_PROGRESS'
        assignment.save()
        
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Complete production",
        description="Mark production assignment as completed.",
        request={'application/json': {'type': 'object', 'properties': {
            'completion_notes': {'type': 'string', 'description': 'Notes about completion'}
        }}}
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete production work."""
        assignment = self.get_object()
        
        if assignment.status not in ['PENDING', 'IN_PROGRESS']:
            return Response(
                {'detail': 'Can only complete pending or in-progress assignments.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignment.status = 'COMPLETED'
        assignment.completion_notes = request.data.get('completion_notes', '')
        assignment.save()
        
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get assignment files",
        description="List all files (galleys) associated with this production assignment."
    )
    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        """Get assignment files."""
        assignment = self.get_object()
        files = assignment.files.all().order_by('-created_at')
        serializer = ProductionFileSerializer(files, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get assignment discussions",
        description="List all discussions for this production assignment."
    )
    @action(detail=True, methods=['get'])
    def discussions(self, request, pk=None):
        """Get assignment discussions."""
        assignment = self.get_object()
        discussions = assignment.discussions.all().order_by('-updated_at')
        serializer = ProductionDiscussionListSerializer(discussions, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get assignment participants",
        description="List all participants involved in this production assignment."
    )
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Get all participants (production assistant, editor, author)."""
        assignment = self.get_object()
        from apps.users.serializers import ProfileSerializer
        
        participants = [
            {**ProfileSerializer(assignment.production_assistant).data, 'role': 'production_assistant'},
            {**ProfileSerializer(assignment.assigned_by).data, 'role': 'assigned_by'},
            {**ProfileSerializer(assignment.submission.corresponding_author).data, 'role': 'author'},
        ]
        
        return Response(participants)


@extend_schema_view(
    list=extend_schema(
        summary="List production files (galleys)",
        description="Get paginated list of production files filtered by assignment, submission, file type, or galley format."
    ),
    retrieve=extend_schema(
        summary="Get production file",
        description="Get detailed information about a specific production file (galley)."
    ),
    create=extend_schema(
        summary="Upload production file (galley)",
        description="Upload a new production file or galley (PDF, HTML, XML, etc.)."
    ),
)
class ProductionFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing production files (galleys).
    
    Handles upload, download, and management of galley files for publication.
    """
    queryset = ProductionFile.objects.all()
    serializer_class = ProductionFileSerializer
    permission_classes = [WorkflowPermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['assignment', 'submission', 'file_type', 'galley_format', 'is_published', 'is_approved']
    search_fields = ['original_filename', 'label', 'description']
    ordering_fields = ['created_at', 'version']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        queryset = ProductionFile.objects.select_related(
            'assignment__submission', 'uploaded_by__user', 'approved_by__user'
        )
        
        # Admin sees all
        if user.is_superuser or user.is_staff:
            return queryset
        
        if hasattr(user, 'profile'):
            # Filter based on assignments user has access to
            from apps.journals.models import JournalStaff
            staff_journals = JournalStaff.objects.filter(
                profile=user.profile,
                is_active=True
            ).values_list('journal_id', flat=True)
            
            return queryset.filter(
                Q(assignment__production_assistant=user.profile) |
                Q(submission__journal_id__in=staff_journals) |
                Q(submission__corresponding_author=user.profile)
            ).distinct()
        
        return queryset.none()
    
    @extend_schema(
        summary="Approve production file",
        description="Approve a production file (galley) for publication."
    )
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve production file."""
        file_obj = self.get_object()
        
        if file_obj.is_approved:
            return Response(
                {'detail': 'File is already approved.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        file_obj.is_approved = True
        file_obj.approved_by = request.user.profile if hasattr(request.user, 'profile') else None
        file_obj.approved_at = timezone.now()
        file_obj.save()
        
        serializer = self.get_serializer(file_obj)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Publish galley file",
        description="Publish an approved galley file to make it visible to readers."
    )
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish galley file."""
        file_obj = self.get_object()
        
        if not file_obj.is_approved:
            return Response(
                {'detail': 'Can only publish approved files.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if file_obj.is_published:
            return Response(
                {'detail': 'File is already published.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        file_obj.is_published = True
        file_obj.published_at = timezone.now()
        file_obj.save()
        
        serializer = self.get_serializer(file_obj)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List production discussions",
        description="Get paginated list of production discussions filtered by assignment, submission, or status."
    ),
    retrieve=extend_schema(
        summary="Get production discussion",
        description="Get detailed information about a specific production discussion with all messages."
    ),
    create=extend_schema(
        summary="Create production discussion",
        description="Start a new production discussion thread."
    ),
)
class ProductionDiscussionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing production discussions.
    
    Handles discussion threads between production assistant, author, and editor.
    """
    queryset = ProductionDiscussion.objects.all()
    permission_classes = [WorkflowPermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['assignment', 'submission', 'status', 'started_by']
    search_fields = ['subject']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    http_method_names = ['get', 'post', 'patch', 'delete']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ProductionDiscussionListSerializer
        return ProductionDiscussionSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        queryset = ProductionDiscussion.objects.select_related(
            'assignment__submission', 'started_by__user', 'closed_by__user'
        ).prefetch_related('participants__user', 'messages__author__user')
        
        # Admin sees all
        if user.is_superuser or user.is_staff:
            return queryset
        
        if hasattr(user, 'profile'):
            # Filter discussions where user is participant or has access to submission
            from apps.journals.models import JournalStaff
            staff_journals = JournalStaff.objects.filter(
                profile=user.profile,
                is_active=True
            ).values_list('journal_id', flat=True)
            
            return queryset.filter(
                Q(participants=user.profile) |
                Q(submission__journal_id__in=staff_journals) |
                Q(submission__corresponding_author=user.profile)
            ).distinct()
        
        return queryset.none()
    
    @extend_schema(
        summary="Add message to discussion",
        description="Add a new message to this production discussion thread.",
        request=ProductionMessageSerializer
    )
    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """Add message to discussion."""
        discussion = self.get_object()
        
        if discussion.status == 'CLOSED':
            return Response(
                {'detail': 'Cannot add messages to closed discussion.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ProductionMessageSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            message = serializer.save(discussion=discussion)
            
            # Add author as participant if not already
            if hasattr(request.user, 'profile'):
                discussion.participants.add(request.user.profile)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Close discussion",
        description="Close this production discussion thread."
    )
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close discussion."""
        discussion = self.get_object()
        
        if discussion.status == 'CLOSED':
            return Response(
                {'detail': 'Discussion is already closed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        discussion.status = 'CLOSED'
        discussion.closed_by = request.user.profile if hasattr(request.user, 'profile') else None
        discussion.closed_at = timezone.now()
        discussion.save()
        
        serializer = self.get_serializer(discussion)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Reopen discussion",
        description="Reopen a closed production discussion thread."
    )
    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """Reopen closed discussion."""
        discussion = self.get_object()
        
        if discussion.status == 'OPEN':
            return Response(
                {'detail': 'Discussion is already open.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        discussion.status = 'OPEN'
        discussion.closed_by = None
        discussion.closed_at = None
        discussion.save()
        
        serializer = self.get_serializer(discussion)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List publication schedules",
        description="Get paginated list of publication schedules filtered by submission or status."
    ),
    retrieve=extend_schema(
        summary="Get publication schedule",
        description="Get detailed information about a specific publication schedule."
    ),
    create=extend_schema(
        summary="Schedule publication",
        description="Schedule a submission for publication. Moves submission to SCHEDULED status."
    ),
    update=extend_schema(
        summary="Update publication schedule",
        description="Update publication schedule details (date, volume, issue, DOI, etc.)."
    ),
)
class PublicationScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing publication schedules.
    
    Handles scheduling of submissions for publication with metadata.
    """
    queryset = PublicationSchedule.objects.all()
    serializer_class = PublicationScheduleSerializer
    permission_classes = [WorkflowPermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['submission', 'status', 'year', 'volume', 'issue']
    search_fields = ['submission__title', 'doi']
    ordering_fields = ['scheduled_date', 'published_date', 'created_at']
    ordering = ['-scheduled_date']
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        queryset = PublicationSchedule.objects.select_related(
            'submission', 'scheduled_by__user'
        )
        
        # Admin sees all
        if user.is_superuser or user.is_staff:
            return queryset
        
        if hasattr(user, 'profile'):
            # Filter based on journal staff
            from apps.journals.models import JournalStaff
            staff_journals = JournalStaff.objects.filter(
                profile=user.profile,
                is_active=True
            ).values_list('journal_id', flat=True)
            
            return queryset.filter(
                Q(submission__journal_id__in=staff_journals) |
                Q(submission__corresponding_author=user.profile)
            ).distinct()
        
        return queryset.none()
    
    @extend_schema(
        summary="Publish now",
        description="Immediately publish a scheduled submission."
    )
    @action(detail=True, methods=['post'])
    def publish_now(self, request, pk=None):
        """Publish submission immediately."""
        schedule = self.get_object()
        
        if schedule.status == 'PUBLISHED':
            return Response(
                {'detail': 'Submission is already published.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        schedule.status = 'PUBLISHED'
        schedule.published_date = timezone.now()
        schedule.save()
        
        # Update submission status
        schedule.submission.status = 'PUBLISHED'
        schedule.submission.save()
        
        serializer = self.get_serializer(schedule)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Cancel publication",
        description="Cancel a scheduled publication."
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel publication schedule."""
        schedule = self.get_object()
        
        if schedule.status == 'PUBLISHED':
            return Response(
                {'detail': 'Cannot cancel published submission.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        schedule.status = 'CANCELLED'
        schedule.save()
        
        # Revert submission status
        schedule.submission.status = 'IN_PRODUCTION'
        schedule.submission.save()
        
        serializer = self.get_serializer(schedule)
        return Response(serializer.data)
