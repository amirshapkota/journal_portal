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

from ...models.copyediting.models import (
    CopyeditingAssignment, CopyeditingFile, CopyeditingDiscussion,
    CopyeditingMessage, CopyeditingMessageAttachment
)
from ...models.production.models import (
    ProductionAssignment, ProductionFile, ProductionDiscussion,
    ProductionMessage, ProductionMessageAttachment, PublicationSchedule
)
from ...serializers.workflow.serializers import (
    CopyeditingAssignmentSerializer, CopyeditingAssignmentListSerializer,
    CopyeditingFileSerializer, CopyeditingDiscussionSerializer,
    CopyeditingDiscussionListSerializer, CopyeditingMessageSerializer,
    ProductionAssignmentSerializer, ProductionAssignmentListSerializer,
    ProductionFileSerializer, ProductionDiscussionSerializer,
    ProductionDiscussionListSerializer, ProductionMessageSerializer,
    PublicationScheduleSerializer
)
from ...models.models import Submission


class WorkflowPermissions(permissions.BasePermission):
    """
    Custom permissions for workflow management.
    - Editors and journal staff can manage workflow
    - Copyeditors/Production assistants can manage their assigned tasks
    - Authors can view their submission's workflow
    - JOURNAL_MANAGER role cannot access workflow (editorial activities)
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
        
        # Explicitly deny JOURNAL_MANAGER role from workflow/editorial activities
        if hasattr(user, 'profile'):
            from apps.users.models import Role
            if user.profile.roles.filter(name='JOURNAL_MANAGER').exists():
                logger.warning(f"Permission DENIED: User has JOURNAL_MANAGER role (no editorial access)")
                return False
        
        if hasattr(user, 'profile'):
            logger.info(f"User has profile: {user.profile.id}")
            # Get submission and assignment based on object type
            submission = None
            assignment = None
            
            if hasattr(obj, 'submission'):
                submission = obj.submission
            elif isinstance(obj, Submission):
                submission = obj
            
            # Get assignment for permission checking
            if hasattr(obj, 'assignment'):
                assignment = obj.assignment
            elif hasattr(obj, 'copyeditor'):
                # This is a CopyeditingAssignment
                assignment = obj
            elif hasattr(obj, 'production_assistant'):
                # This is a ProductionAssignment
                assignment = obj
            
            if submission:
                logger.info(f"Submission found: {submission.id}, journal: {submission.journal.id}")
                
                # Journal staff permissions (check first - staff can do everything)
                from apps.journals.models import JournalStaff
                is_staff = JournalStaff.objects.filter(
                    journal=submission.journal,
                    profile=user.profile,
                    is_active=True
                ).exists()
                if is_staff:
                    logger.info(f"Permission GRANTED: User is journal staff")
                    return True
                
                # Copyeditor permissions - check both direct and via assignment
                # If object has copyeditor directly (CopyeditingAssignment)
                if hasattr(obj, 'copyeditor') and obj.copyeditor == user.profile:
                    logger.info(f"Permission GRANTED: User is copyeditor (direct)")
                    return True
                
                # If object belongs to an assignment where user is copyeditor
                if assignment and hasattr(assignment, 'copyeditor') and assignment.copyeditor == user.profile:
                    logger.info(f"Permission GRANTED: User is copyeditor (via assignment)")
                    return True
                
                # Production assistant permissions - check both direct and via assignment
                if hasattr(obj, 'production_assistant') and obj.production_assistant == user.profile:
                    logger.info(f"Permission GRANTED: User is production assistant (direct)")
                    return True
                
                if assignment and hasattr(assignment, 'production_assistant') and assignment.production_assistant == user.profile:
                    logger.info(f"Permission GRANTED: User is production assistant (via assignment)")
                    return True
                
                # Check if user is a participant
                if hasattr(obj, 'participants'):
                    if obj.participants.filter(id=user.profile.id).exists():
                        logger.info(f"Permission GRANTED: User is a participant")
                        return True
                
                # Allow the assigner to manage the assignment
                if hasattr(obj, 'assigned_by') and obj.assigned_by == user.profile:
                    logger.info(f"Permission GRANTED: User is assigner (assigned_by)")
                    return True
                
                if assignment and hasattr(assignment, 'assigned_by') and assignment.assigned_by == user.profile:
                    logger.info(f"Permission GRANTED: User is assigner (via assignment)")
                    return True
                
                # Allow the scheduler to manage publication schedules
                if hasattr(obj, 'scheduled_by') and obj.scheduled_by == user.profile:
                    logger.info(f"Permission GRANTED: User is scheduler (scheduled_by)")
                    return True
                
                # Author permissions (read-only) - check last
                if submission.corresponding_author == user.profile:
                    result = request.method in permissions.SAFE_METHODS or view.action in ['add_message']
                    logger.info(f"Author check: {result}")
                    return result
                    
                logger.warning(f"Permission DENIED: No matching permission found")
            else:
                logger.warning(f"Permission DENIED: No submission found")
        else:
            logger.warning(f"Permission DENIED: User has no profile")
        
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
        
        # Send notification to author
        from apps.notifications.tasks import send_copyediting_started_email
        try:
            send_copyediting_started_email.delay(str(assignment.id))
        except Exception as e:
            logger.error(f"Failed to send copyediting started notification: {e}")
        
        # Create copyediting files from submission documents
        from django.core.files.base import ContentFile
        import logging
        logger = logging.getLogger(__name__)
        
        files_created = 0
        files_failed = 0
        
        # Get submission documents (manuscripts and supplementary files)
        submission_docs = assignment.submission.documents.filter(
            document_type__in=['MANUSCRIPT', 'SUPPLEMENTARY', 'REVISED_MANUSCRIPT']
        )
        
        logger.info(f"Found {submission_docs.count()} submission documents to process for assignment {assignment.id}")
        
        for doc in submission_docs:
            logger.info(f"Processing document {doc.id}: {doc.file_name} (type: {doc.document_type})")
            
            # Skip if copyediting file already exists for this document
            existing = CopyeditingFile.objects.filter(
                assignment=assignment,
                submission=assignment.submission,
                original_filename=doc.file_name
            ).exists()
            
            if existing:
                logger.info(f"Skipping document {doc.id} - copyediting file already exists")
                continue
            
            # Create copyediting file from document
            try:
                # Determine mime type safely
                mime_type = 'application/octet-stream'
                if doc.original_file:
                    try:
                        if hasattr(doc.original_file, 'file') and hasattr(doc.original_file.file, 'content_type'):
                            mime_type = doc.original_file.file.content_type
                    except:
                        pass
                
                copyediting_file = CopyeditingFile.objects.create(
                    assignment=assignment,
                    submission=assignment.submission,
                    file_type='INITIAL_DRAFT',
                    description=f'Initial draft from submission document: {doc.title}',
                    uploaded_by=request.user.profile if hasattr(request.user, 'profile') else assignment.assigned_by,
                    original_filename=doc.file_name,
                    file_size=doc.file_size,
                    mime_type=mime_type,
                    version=1
                )
                
                logger.info(f"Created copyediting file record {copyediting_file.id} for document {doc.id}")
                
                # Copy the file content
                if doc.original_file and hasattr(doc.original_file, 'file'):
                    try:
                        doc.original_file.file.seek(0)
                        file_content = doc.original_file.file.read()
                        copyediting_file.file.save(
                            doc.file_name,
                            ContentFile(file_content),
                            save=True
                        )
                        files_created += 1
                        logger.info(f"Successfully copied file content for document {doc.id}")
                    except Exception as file_copy_error:
                        logger.error(f"Error copying file content for document {doc.id}: {str(file_copy_error)}", exc_info=True)
                        # Delete the copyediting file if file copy failed
                        copyediting_file.delete()
                        files_failed += 1
                else:
                    logger.warning(f"Document {doc.id} has no original_file or file attribute")
                    # Keep the copyediting file record even if no file content
                    files_created += 1
            except Exception as e:
                # Log error but continue with other files
                logger.error(f"Error creating copyediting file from document {doc.id}: {str(e)}", exc_info=True)
                files_failed += 1
        
        logger.info(f"Copyediting file creation complete: {files_created} created, {files_failed} failed")
        
        serializer = self.get_serializer(assignment)
        return Response({
            **serializer.data,
            'files_created': files_created,
            'files_failed': files_failed,
            'total_documents': submission_docs.count()
        })
    
    @extend_schema(
        summary="Complete copyediting",
        description="Mark copyediting assignment as completed. Validates all files are in AUTHOR_FINAL status, moves them to FINAL, and transitions submission to production.",
        request={'application/json': {'type': 'object', 'properties': {
            'completion_notes': {'type': 'string', 'description': 'Notes about completion'}
        }}}
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete copyediting work and transition to production."""
        assignment = self.get_object()
        
        # Validate assignment status
        if assignment.status not in ['PENDING', 'IN_PROGRESS']:
            return Response(
                {'detail': 'Can only complete pending or in-progress assignments.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate all required files are in AUTHOR_FINAL status
        author_final_files = CopyeditingFile.objects.filter(
            assignment=assignment,
            file_type='AUTHOR_FINAL'
        )
        
        if not author_final_files.exists():
            return Response(
                {'detail': 'No files have been confirmed by the author. All copyedited files must be reviewed and confirmed by the author before completion.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check for any COPYEDITED files that haven't been confirmed
        unconfirmed_files = CopyeditingFile.objects.filter(
            assignment=assignment,
            file_type='COPYEDITED'
        )
        
        if unconfirmed_files.exists():
            unconfirmed_count = unconfirmed_files.count()
            return Response(
                {'detail': f'{unconfirmed_count} copyedited file(s) have not been confirmed by the author. All files must be reviewed and confirmed before completion.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Move all AUTHOR_FINAL files to FINAL status
        from django.utils import timezone
        files_finalized = author_final_files.update(
            file_type='FINAL',
            last_edited_at=timezone.now()
        )
        
        # Update assignment status
        assignment.status = 'COMPLETED'
        assignment.completion_notes = request.data.get('completion_notes', '')
        assignment.completed_at = timezone.now()
        assignment.save()
        
        # Update submission status to production-ready
        submission = assignment.submission
        if submission.status in ['ACCEPTED', 'COPYEDITING']:
            submission.status = 'PRODUCTION'
            submission.save()
        
        # Send notification to editor and author
        from apps.notifications.tasks import send_copyediting_completed_email
        try:
            send_copyediting_completed_email.delay(str(assignment.id))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send copyediting completed notification: {e}")
        
        serializer = self.get_serializer(assignment)
        
        return Response({
            'status': 'completed',
            'message': 'Copyediting completed successfully',
            'assignment_id': str(assignment.id),
            'assignment_status': assignment.status,
            'submission_status': submission.status,
            'files_finalized': files_finalized,
            'completed_at': assignment.completed_at,
            'completed_by': {
                'id': str(request.user.profile.id) if hasattr(request.user, 'profile') else None,
                'name': request.user.profile.display_name if hasattr(request.user, 'profile') else request.user.get_full_name(),
                'email': request.user.email
            },
            'completion_notes': assignment.completion_notes,
            'assignment': serializer.data
        })
    
    @extend_schema(
        summary="Get assignment files",
        description="List all files associated with this copyediting assignment."
    )
    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        """Get assignment files, optionally filter by file_type."""
        assignment = self.get_object()
        files = assignment.files.all()
        file_type = request.query_params.get('file_type')
        if file_type:
            files = files.filter(file_type=file_type)
        files = files.order_by('-created_at')
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
        from apps.users.serializers.serializers import ProfileSerializer
        
        participants = [
            {**ProfileSerializer(assignment.copyeditor).data, 'role': 'copyeditor'},
            {**ProfileSerializer(assignment.assigned_by).data, 'role': 'assigned_by'},
            {**ProfileSerializer(assignment.submission.corresponding_author).data, 'role': 'author'},
        ]
        
        # Add additional participants
        for participant in assignment.participants.all():
            participants.append({
                **ProfileSerializer(participant).data,
                'role': 'participant'
            })
        
        return Response(participants)
    
    @extend_schema(
        summary="Add participant to assignment",
        description="Add an additional participant/collaborator to this copyediting assignment.",
        request={'application/json': {'type': 'object', 'properties': {
            'profile_id': {'type': 'string', 'format': 'uuid', 'description': 'Profile UUID of the user to add'}
        }, 'required': ['profile_id']}}
    )
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add a participant to the assignment."""
        assignment = self.get_object()
        profile_id = request.data.get('profile_id')
        
        if not profile_id:
            return Response(
                {'detail': 'profile_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.users.models import Profile
        try:
            profile = Profile.objects.get(id=profile_id)
        except Profile.DoesNotExist:
            return Response(
                {'detail': 'Profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already a participant
        if assignment.participants.filter(id=profile_id).exists():
            return Response(
                {'detail': 'User is already a participant.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is already the copyeditor or assigned_by
        if profile == assignment.copyeditor:
            return Response(
                {'detail': 'User is already the assigned copyeditor.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if profile == assignment.assigned_by:
            return Response(
                {'detail': 'User is already the assigner.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add participant
        assignment.participants.add(profile)
        
        return Response(
            {'detail': 'Participant added successfully.'},
            status=status.HTTP_201_CREATED
        )
    
    @extend_schema(
        summary="Get copyedited files",
        description="Get all files with COPYEDITED status for author review."
    )
    @action(detail=True, methods=['get'], url_path='copyedited-files')
    def copyedited_files(self, request, pk=None):
        """Get all copyedited files for this assignment."""
        assignment = self.get_object()
        
        # Get all files with COPYEDITED status
        files = CopyeditingFile.objects.filter(
            assignment=assignment,
            file_type='COPYEDITED'
        ).select_related('uploaded_by__user').order_by('-created_at')
        
        serializer = CopyeditingFileSerializer(files, many=True, context={'request': request})
        
        return Response({
            'count': files.count(),
            'results': serializer.data
        })
    
    @extend_schema(
        summary="Remove participant from assignment",
        description="Remove a participant/collaborator from this copyediting assignment.",
        request={'application/json': {'type': 'object', 'properties': {
            'profile_id': {'type': 'string', 'format': 'uuid', 'description': 'Profile UUID of the user to remove'}
        }, 'required': ['profile_id']}}
    )
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """Remove a participant from the assignment."""
        assignment = self.get_object()
        profile_id = request.data.get('profile_id')
        
        if not profile_id:
            return Response(
                {'detail': 'profile_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if participant exists
        if not assignment.participants.filter(id=profile_id).exists():
            return Response(
                {'detail': 'User is not a participant.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Remove participant
        assignment.participants.remove(profile_id)
        
        return Response(
            {'detail': 'Participant removed successfully.'},
            status=status.HTTP_200_OK
        )


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
        description="Approve a copyediting file for further processing. Updates file type to COPYEDITED."
    )
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve copyediting file and update status to COPYEDITED."""
        file_obj = self.get_object()
        
        if file_obj.is_approved:
            return Response(
                {'detail': 'File is already approved.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        file_obj.is_approved = True
        file_obj.file_type = 'COPYEDITED'  # Update file type to COPYEDITED
        file_obj.approved_by = request.user.profile if hasattr(request.user, 'profile') else None
        file_obj.approved_at = timezone.now()
        file_obj.save()
        
        # Send notification to author that file is ready for review
        from apps.notifications.tasks import send_copyedited_file_ready_email
        try:
            send_copyedited_file_ready_email.delay(str(file_obj.id))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send copyedited file ready notification: {e}")
        
        serializer = self.get_serializer(file_obj)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Load file for editing",
        description="Load copyediting file metadata and URL for editing in document editor (e.g., SuperDoc)."
    )
    @action(detail=True, methods=['get'], url_path='load')
    def load_file(self, request, pk=None):
        """
        Load copyediting file for editing.
        Returns file metadata and download URL.
        Similar to SuperDoc's load_document endpoint.
        """
        file_obj = self.get_object()
        
        response_data = {
            'id': str(file_obj.id),
            'assignment_id': str(file_obj.assignment.id),
            'submission_id': str(file_obj.submission.id),
            'file_type': file_obj.file_type,
            'file_type_display': file_obj.get_file_type_display(),
            'original_filename': file_obj.original_filename,
            'description': file_obj.description,
            'version': file_obj.version,
            'is_approved': file_obj.is_approved,
            'created_at': file_obj.created_at,
            'updated_at': file_obj.updated_at,
            'last_edited_at': file_obj.last_edited_at,
            'last_edited_by': None,
            'file_url': None,
            'file_size': None,
            'mime_type': None,
        }
        
        # Add last editor info
        if file_obj.last_edited_by:
            response_data['last_edited_by'] = {
                'id': str(file_obj.last_edited_by.id),
                'name': file_obj.last_edited_by.display_name,
                'email': file_obj.last_edited_by.user.email,
            }
        
        # Add file details if exists
        if file_obj.file:
            response_data['file_url'] = request.build_absolute_uri(file_obj.file.url)
            response_data['file_size'] = file_obj.file_size
            response_data['mime_type'] = file_obj.mime_type
        
        return Response(response_data)
    
    @extend_schema(
        summary="Save file (manual save)",
        description="Save the updated file, replacing the existing one. Does NOT create a new version - this is for intermediate saves during editing.",
        request={'multipart/form-data': {'type': 'object', 'properties': {
            'file': {'type': 'string', 'format': 'binary', 'description': 'The file to upload'}
        }}}
    )
    @action(detail=True, methods=['post'], url_path='save')
    def save_file(self, request, pk=None):
        """
        Save copyediting file (manual save workflow like SuperDoc).
        
        This REPLACES the existing file with the updated one.
        The old file is automatically deleted.
        
        Use this for:
        - Copyeditor saving progress while editing
        - Intermediate saves during the editing process
        
        For creating a new version (e.g., after copyeditor completes work),
        use the regular POST endpoint to create a new CopyeditingFile with
        file_type='COPYEDITED'.
        """
        file_obj = self.get_object()
        uploaded_file = request.FILES.get('file')
        
        if not uploaded_file:
            return Response(
                {'detail': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Store reference to old file
        old_file_path = None
        if file_obj.file:
            try:
                old_file_path = file_obj.file.path
            except:
                old_file_path = None
        
        # Update file
        file_obj.file = uploaded_file
        file_obj.file_size = uploaded_file.size
        file_obj.original_filename = uploaded_file.name
        
        # Detect mime type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(uploaded_file.name)
        file_obj.mime_type = mime_type or 'application/octet-stream'
        
        # Update edit tracking
        from django.utils import timezone
        file_obj.last_edited_at = timezone.now()
        if hasattr(request.user, 'profile'):
            file_obj.last_edited_by = request.user.profile
        
        file_obj.save()
        
        # Delete old file after saving new one
        if old_file_path:
            try:
                import os
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to delete old file {old_file_path}: {str(e)}")
        
        serializer = self.get_serializer(file_obj)
        return Response({
            'status': 'saved',
            'message': 'File saved successfully',
            'file': serializer.data
        })
    
    @extend_schema(
        summary="Download copyediting file",
        description="Download the copyediting file."
    )
    @action(detail=True, methods=['get'], url_path='download')
    def download_file(self, request, pk=None):
        """Download the copyediting file."""
        file_obj = self.get_object()
        
        if not file_obj.file:
            return Response(
                {'detail': 'No file available for download.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        from django.http import FileResponse
        
        response = FileResponse(
            file_obj.file.open('rb'),
            content_type=file_obj.mime_type
        )
        response['Content-Disposition'] = f'attachment; filename="{file_obj.original_filename}"'
        
        return response
    
    @extend_schema(
        summary="Author confirms file as final",
        description="Allow authors to review copyedited files and mark them as final.",
        request={'application/json': {'type': 'object', 'properties': {
            'confirmation_notes': {'type': 'string', 'description': 'Optional notes from author about the confirmation'}
        }}}
    )
    @action(detail=True, methods=['post'], url_path='confirm-final')
    def confirm_final(self, request, pk=None):
        """Author confirms copyedited file as final."""
        file_obj = self.get_object()
        
        # Validate file is in COPYEDITED status
        if file_obj.file_type != 'COPYEDITED':
            return Response(
                {'detail': 'Only COPYEDITED files can be confirmed by author.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate user is the submission author
        if not hasattr(request.user, 'profile'):
            return Response(
                {'detail': 'User profile not found.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if file_obj.submission.corresponding_author != request.user.profile:
            return Response(
                {'detail': 'Only the submission author can confirm files.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update file status to AUTHOR_FINAL
        from django.utils import timezone
        file_obj.file_type = 'AUTHOR_FINAL'
        file_obj.description = request.data.get('confirmation_notes', file_obj.description)
        file_obj.last_edited_at = timezone.now()
        file_obj.last_edited_by = request.user.profile
        file_obj.save()
        
        # Send notification to editor that file is confirmed
        # (We send copyedited_file_ready when file type changes to COPYEDITED)
        
        serializer = self.get_serializer(file_obj)
        return Response({
            'status': 'confirmed',
            'message': 'File confirmed as final by author',
            'file': serializer.data,
            'confirmed_at': file_obj.last_edited_at,
            'confirmed_by': {
                'id': str(request.user.profile.id),
                'name': request.user.profile.display_name,
                'email': request.user.email
            },
            'confirmation_notes': file_obj.description
        })


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
        
        # Send notification to author
        from apps.notifications.tasks import send_production_started_email
        try:
            send_production_started_email.delay(str(assignment.id))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send production started notification: {e}")
        
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
        
        from django.utils import timezone
        assignment.status = 'COMPLETED'
        assignment.completion_notes = request.data.get('completion_notes', '')
        assignment.completed_at = timezone.now()
        assignment.save()
        
        # Send notification to editor and author
        from apps.notifications.tasks import send_production_completed_email
        try:
            send_production_completed_email.delay(str(assignment.id))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send production completed notification: {e}")
        
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
        from apps.users.serializers.serializers import ProfileSerializer
        
        participants = [
            {**ProfileSerializer(assignment.production_assistant).data, 'role': 'production_assistant'},
            {**ProfileSerializer(assignment.assigned_by).data, 'role': 'assigned_by'},
            {**ProfileSerializer(assignment.submission.corresponding_author).data, 'role': 'author'},
        ]
        
        # Add additional participants
        for participant in assignment.participants.all():
            participants.append({
                **ProfileSerializer(participant).data, 
                'role': 'participant'
            })
        
        return Response(participants)
    
    @extend_schema(
        summary="Add participant to assignment",
        description="Add an additional participant/collaborator to this production assignment.",
        request={'application/json': {'type': 'object', 'properties': {
            'profile_id': {'type': 'string', 'format': 'uuid', 'description': 'Profile UUID of the user to add'}
        }, 'required': ['profile_id']}}
    )
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add a participant to this production assignment."""
        assignment = self.get_object()
        
        profile_id = request.data.get('profile_id')
        if not profile_id:
            return Response(
                {'error': 'profile_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists
        from apps.users.models import Profile
        try:
            profile = Profile.objects.get(id=profile_id)
        except Profile.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already a participant
        if assignment.participants.filter(id=profile_id).exists():
            return Response(
                {'error': 'User is already a participant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already the production assistant or assigned_by
        if profile.id == assignment.production_assistant.id:
            return Response(
                {'error': 'User is already the production assistant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if profile.id == assignment.assigned_by.id:
            return Response(
                {'error': 'User is already the assigner (editor)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add participant
        assignment.participants.add(profile)
        
        from apps.users.serializers.serializers import ProfileSerializer
        return Response(
            ProfileSerializer(profile).data,
            status=status.HTTP_201_CREATED
        )
    
    @extend_schema(
        summary="Remove participant from assignment",
        description="Remove a participant/collaborator from this production assignment.",
        request={'application/json': {'type': 'object', 'properties': {
            'profile_id': {'type': 'string', 'format': 'uuid', 'description': 'Profile UUID of the user to remove'}
        }, 'required': ['profile_id']}}
    )
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """Remove a participant from this production assignment."""
        assignment = self.get_object()
        
        profile_id = request.data.get('profile_id')
        if not profile_id:
            return Response(
                {'error': 'profile_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is a participant
        if not assignment.participants.filter(id=profile_id).exists():
            return Response(
                {'error': 'User is not a participant'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Remove participant
        assignment.participants.remove(profile_id)
        
        return Response(
            {'message': 'Participant removed successfully'},
            status=status.HTTP_200_OK
        )


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
        
        # Send notification to author
        from apps.notifications.tasks import send_galley_published_email
        try:
            send_galley_published_email.delay(str(file_obj.id))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send galley published notification: {e}")
        
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
    
    def perform_create(self, serializer):
        """Create publication schedule and send notification."""
        schedule = serializer.save()
        
        # Update submission status
        schedule.submission.status = 'SCHEDULED'
        schedule.submission.save()
        
        # Send notification to author
        from apps.notifications.tasks import send_publication_scheduled_email
        try:
            send_publication_scheduled_email.delay(str(schedule.id))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send publication scheduled notification: {e}")
    
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
        
        # Send notification to author
        from apps.notifications.tasks import send_publication_published_email
        try:
            send_publication_published_email.delay(str(schedule.id))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send publication published notification: {e}")
        
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
        
        # Send notification to author
        from apps.notifications.tasks import send_publication_cancelled_email
        try:
            send_publication_cancelled_email.delay(str(schedule.id))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send publication cancelled notification: {e}")
        
        serializer = self.get_serializer(schedule)
        return Response(serializer.data)
