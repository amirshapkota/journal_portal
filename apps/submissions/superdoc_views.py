"""
SuperDoc Integration ViewSet.
Handles document management for SuperDoc editor.
Comments and formatting are stored within the DOCX file itself.
Manual save workflow - no real-time collaboration (no Yjs needed).
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import FileResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models.models import Submission, Document, AuthorContribution
from .serializers.superdoc.serializers import SuperDocCreateSerializer, SuperDocMetadataSerializer
from apps.users.models import Profile
from apps.reviews.models import ReviewAssignment


class SuperDocPermission(permissions.BasePermission):
    """
    Custom permission for SuperDoc documents.
    
    Rules:
    - Admin/staff: full access to all documents
    - Corresponding author: full access (view + edit)
    - Co-authors: view and comment only (edit=False)
    - Reviewers: view and comment only (edit=False)
    - Journal editors: full access
    - JOURNAL_MANAGER: no access (editorial activities)
    - Others: no access
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access this specific document."""
        document = obj
        user = request.user
        
        # Admin/staff - full access
        if user.is_superuser or user.is_staff:
            return True
        
        # Must have profile
        profile = getattr(user, 'profile', None)
        if not profile:
            return False
        
        # Explicitly deny JOURNAL_MANAGER role from editorial activities
        from apps.users.models import Role
        if profile.roles.filter(name='JOURNAL_MANAGER').exists():
            return False
        
        submission = document.submission
        
        # Corresponding author - full access
        if submission.corresponding_author == profile:
            return True
        
        # Co-authors - view only (edit check handled separately)
        if AuthorContribution.objects.filter(submission=submission, profile=profile).exists():
            return True
        
        # Reviewers - view and comment access
        if ReviewAssignment.objects.filter(submission=submission, reviewer=profile).exists():
            return True
        
        # Journal editors - full access
        from apps.journals.models import JournalStaff
        if JournalStaff.objects.filter(journal=submission.journal, profile=profile, is_active=True).exists():
            return True
        
        return False


def can_access_document(user, document):
    """
    Check if user can access this document based on submission permissions.
    Returns (can_view, can_edit) tuple.
    """
    if not user.is_authenticated:
        return (False, False)
    
    if user.is_superuser or user.is_staff:
        return (True, True)
    
    submission = document.submission
    profile = getattr(user, 'profile', None)
    
    if not profile:
        return (False, False)
    
    # Explicitly deny JOURNAL_MANAGER role from editorial activities
    from apps.users.models import Role
    if profile.roles.filter(name='JOURNAL_MANAGER').exists():
        return (False, False)
    
    # Corresponding author - full access
    if submission.corresponding_author == profile:
        return (True, True)
    
    # Co-authors - can view and comment (edit permission controlled by SuperDoc UI)
    if AuthorContribution.objects.filter(submission=submission, profile=profile).exists():
        return (True, False)
    
    # Reviewers - can view and comment (edit permission controlled by SuperDoc UI)
    if ReviewAssignment.objects.filter(submission=submission, reviewer=profile).exists():
        return (True, True)  # Give edit permission so they can add comments and track changes
    
    # Journal editors - full access
    from apps.journals.models import JournalStaff
    if JournalStaff.objects.filter(journal=submission.journal, profile=profile, is_active=True).exists():
        return (True, True)
    
    return (False, False)


class SuperDocViewSet(viewsets.ViewSet):
    """
    API for SuperDoc integration with manual save workflow.
    
    SuperDoc handles:
    - Comments stored in DOCX file natively
    - Track changes within DOCX
    - Document editing UI
    
    Backend handles:
    - DOCX file storage and retrieval
    - Access permissions
    - Version tracking via updated files
    """
    permission_classes = [SuperDocPermission]
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions that this view requires.
        """
        if self.action == 'create':
            # Only authenticated users can create documents
            return [permissions.IsAuthenticated()]
        return [SuperDocPermission()]
    
    def list(self, request):
        """List all documents user has access to."""
        user = request.user
        profile = getattr(user, 'profile', None)
        
        if not profile:
            return Response([])
        
        # Get documents from user's submissions
        from .models.models import AuthorContribution
        
        documents = Document.objects.filter(
            submission__corresponding_author=profile
        ) | Document.objects.filter(
            submission__coauthors=profile
        )
        
        # Add documents from review assignments
        from apps.reviews.models import ReviewAssignment
        review_submissions = ReviewAssignment.objects.filter(
            reviewer=profile
        ).values_list('submission_id', flat=True)
        
        documents = documents | Document.objects.filter(
            submission_id__in=review_submissions
        )
        
        documents = documents.distinct()
        
        serializer = SuperDocMetadataSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)
    
    def create(self, request):
        """Create a new document."""
        serializer = SuperDocCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            document = serializer.save()
            return Response(
                SuperDocMetadataSerializer(document, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        """Get document metadata."""
        document = get_object_or_404(Document, pk=pk)
        can_view, can_edit = can_access_document(request.user, document)
        
        if not can_view:
            return Response(
                {'error': 'You do not have permission to view this document'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SuperDocMetadataSerializer(document, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="Load document for SuperDoc editor",
        description="Returns document metadata and DOCX file URL",
        responses={
            200: OpenApiResponse(description="Document loaded successfully"),
            403: OpenApiResponse(description="No access to this document"),
            404: OpenApiResponse(description="Document not found"),
        }
    )
    @action(detail=True, methods=['get'], url_path='load')
    def load_document(self, request, pk=None):
        """
        Load document for SuperDoc editor.
        Returns DOCX file URL with all comments embedded.
        """
        document = get_object_or_404(Document, pk=pk)
        can_view, can_edit = can_access_document(request.user, document)
        
        if not can_view:
            return Response(
                {'error': 'You do not have permission to view this document'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Prepare response
        response_data = {
            'id': str(document.id),
            'title': document.title,
            'document_type': document.document_type,
            'can_edit': can_edit,
            'created_at': document.created_at,
            'updated_at': document.updated_at,
            'last_edited_at': document.last_edited_at,
            'last_edited_by': None,
            'file_url': None,
            'file_name': None,
            'file_size': None,
        }
        
        # Add last editor info
        if document.last_edited_by:
            response_data['last_edited_by'] = {
                'id': str(document.last_edited_by.id),
                'name': document.last_edited_by.display_name,
            }
        
        # Add file URL if exists
        if document.original_file:
            response_data['file_url'] = request.build_absolute_uri(document.original_file.url)
            response_data['file_name'] = document.file_name
            response_data['file_size'] = document.file_size
        
        return Response(response_data)
    
    @extend_schema(
        summary="Save document (manual save)",
        description="Save the current DOCX file with all edits and comments embedded. Replaces the existing file - does NOT create a version.",
        responses={
            200: OpenApiResponse(description="Document saved successfully"),
            403: OpenApiResponse(description="No edit access to this document"),
            400: OpenApiResponse(description="No file provided"),
        }
    )
    @action(detail=True, methods=['post'], url_path='save')
    def save_document(self, request, pk=None):
        """
        Save document from SuperDoc editor (manual save).
        
        This endpoint REPLACES the existing DOCX file with the updated one.
        The old file is automatically deleted by Django's FileField.
        
        Version creation happens separately when:
        - Author submits the document for review
        - Author submits a revision after review
        
        Use this endpoint for:
        - Author making edits and saving progress
        - Reviewer adding comments and saving
        - Any intermediate saves during editing
        """
        document = get_object_or_404(Document, pk=pk)
        can_view, can_edit = can_access_document(request.user, document)
        
        if not can_edit:
            return Response(
                {'error': 'You do not have permission to edit this document'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        docx_file = request.FILES.get('file')
        
        if not docx_file:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file type
        if not docx_file.name.endswith('.docx'):
            return Response(
                {'error': 'File must be a .docx file'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Store reference to old file before replacing
        old_file_path = None
        if document.original_file:
            try:
                old_file_path = document.original_file.path
            except:
                old_file_path = None
        
        # Assign new file
        document.original_file = docx_file
        document.file_name = docx_file.name
        document.file_size = docx_file.size
        document.last_edited_at = timezone.now()
        document.last_edited_by = request.user.profile
        document.save()
        
        # Delete old file after saving new one
        if old_file_path:
            try:
                import os
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            except Exception as e:
                # Log but don't fail if old file deletion fails
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to delete old file {old_file_path}: {str(e)}")
        
        # Return updated metadata
        serializer = SuperDocMetadataSerializer(document, context={'request': request})
        return Response({
            'status': 'saved',
            'message': 'Document saved successfully',
            'document': serializer.data
        })
    
    @extend_schema(
        summary="Create document version",
        description="Create a new version snapshot when submitting document or revision",
        responses={
            201: OpenApiResponse(description="Version created successfully"),
            403: OpenApiResponse(description="No permission to create version"),
            400: OpenApiResponse(description="Invalid request"),
        }
    )
    @action(detail=True, methods=['post'], url_path='create-version')
    def create_version(self, request, pk=None):
        """
        Create a new version of the document.
        
        This should be called when:
        - Author submits the manuscript for review (initial submission)
        - Author submits a revision after receiving reviewer feedback
        
        This creates a snapshot in DocumentVersion table and keeps
        the current document.original_file as the working copy.
        """
        document = get_object_or_404(Document, pk=pk)
        can_view, can_edit = can_access_document(request.user, document)
        
        # Only corresponding author or editors can create versions
        if not can_edit:
            return Response(
                {'error': 'You do not have permission to create versions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not document.original_file:
            return Response(
                {'error': 'No document file to create version from'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get change summary from request
        change_summary = request.data.get('change_summary', '')
        
        # Import DocumentVersion model
        from .models.models import DocumentVersion
        from django.core.files.base import ContentFile
        import hashlib
        import os
        
        # Read file content and calculate hash
        document.original_file.seek(0)
        file_content = document.original_file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        document.original_file.seek(0)
        
        # Get next version number
        last_version = DocumentVersion.objects.filter(
            document=document
        ).order_by('-version_number').first()
        version_number = (last_version.version_number + 1) if last_version else 1
        
        # Create new version with a copy of the file
        version = DocumentVersion(
            document=document,
            version_number=version_number,
            change_summary=change_summary,
            file_name=document.file_name,
            file_size=document.file_size,
            file_hash=file_hash,
            is_current=True,
            created_by=request.user.profile
        )
        
        # Save a copy of the file with versioned filename
        file_extension = os.path.splitext(document.file_name)[1]
        versioned_filename = f"{os.path.splitext(document.file_name)[0]}_v{version_number}{file_extension}"
        version.file.save(versioned_filename, ContentFile(file_content), save=False)
        version.save()
        
        return Response({
            'status': 'created',
            'message': f'Version {version_number} created successfully',
            'version': {
                'id': str(version.id),
                'version_number': version.version_number,
                'change_summary': version.change_summary,
                'file_name': version.file_name,
                'file_size': version.file_size,
                'created_by': version.created_by.display_name,
                'created_at': version.created_at,
            }
        }, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        summary="Download document",
        description="Download the current DOCX file",
        responses={
            200: OpenApiResponse(description="File downloaded"),
            403: OpenApiResponse(description="No access to this document"),
            404: OpenApiResponse(description="No file available"),
        }
    )
    @action(detail=True, methods=['get'], url_path='download')
    def download_docx(self, request, pk=None):
        """
        Download the current DOCX file.
        """
        document = get_object_or_404(Document, pk=pk)
        can_view, can_edit = can_access_document(request.user, document)
        
        if not can_view:
            return Response(
                {'error': 'You do not have permission to view this document'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not document.original_file:
            return Response(
                {'error': 'No file available for download'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Return file response
        response = FileResponse(
            document.original_file.open('rb'),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
        
        return response
    
    @extend_schema(
        summary="Get document versions",
        description="Get all versions for a document",
        responses={
            200: OpenApiResponse(description="List of versions"),
            403: OpenApiResponse(description="No access to this document"),
        }
    )
    @action(detail=True, methods=['get'], url_path='versions')
    def get_versions(self, request, pk=None):
        """
        Get all versions for a document.
        Returns version history ordered by version number (newest first).
        """
        document = get_object_or_404(Document, pk=pk)
        can_view, can_edit = can_access_document(request.user, document)
        
        if not can_view:
            return Response(
                {'error': 'You do not have permission to view this document'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .models.models import DocumentVersion
        
        versions = DocumentVersion.objects.filter(
            document=document
        ).select_related('created_by', 'created_by__user').order_by('-version_number')
        
        versions_data = []
        for version in versions:
            versions_data.append({
                'id': str(version.id),
                'version_number': version.version_number,
                'change_summary': version.change_summary,
                'file_name': version.file_name,
                'file_size': version.file_size,
                'file_hash': version.file_hash,
                'file_url': request.build_absolute_uri(version.file.url) if version.file else None,
                'is_current': version.is_current,
                'immutable_flag': version.immutable_flag,
                'created_by': {
                    'id': str(version.created_by.id),
                    'name': version.created_by.display_name,
                    'email': version.created_by.user.email if version.created_by.user else None,
                },
                'created_at': version.created_at,
            })
        
        return Response({
            'document_id': str(document.id),
            'document_title': document.title,
            'total_versions': len(versions_data),
            'versions': versions_data
        }, status=status.HTTP_200_OK)
    
    @extend_schema(
        summary="Download document version",
        description="Download a specific version of the document",
        responses={
            200: OpenApiResponse(description="File downloaded"),
            403: OpenApiResponse(description="No access to this document"),
            404: OpenApiResponse(description="Version not found or no file available"),
        }
    )
    @action(detail=False, methods=['get'], url_path='versions/(?P<version_id>[^/.]+)/download')
    def download_version(self, request, version_id=None):
        """
        Download a specific version of a document.
        """
        from .models.models import DocumentVersion
        
        version = get_object_or_404(DocumentVersion, pk=version_id)
        document = version.document
        
        can_view, can_edit = can_access_document(request.user, document)
        
        if not can_view:
            return Response(
                {'error': 'You do not have permission to view this document'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not version.file:
            return Response(
                {'error': 'No file available for download'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Return file response
        response = FileResponse(
            version.file.open('rb'),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="{version.file_name}"'
        
        return response
    
    @extend_schema(
        summary="Delete document",
        description="Delete a document and all associated data",
        responses={
            204: OpenApiResponse(description="Document deleted successfully"),
            403: OpenApiResponse(description="No permission to delete this document"),
            404: OpenApiResponse(description="Document not found"),
        }
    )
    def destroy(self, request, pk=None):
        """
        Delete a document.
        Only corresponding author, journal editors, and admin can delete.
        """
        document = get_object_or_404(Document, pk=pk)
        user = request.user
        
        # Check deletion permissions
        can_delete = False
        
        # Admin/staff - can delete
        if user.is_superuser or user.is_staff:
            can_delete = True
        
        profile = getattr(user, 'profile', None)
        if profile:
            submission = document.submission
            
            # Corresponding author - can delete
            if submission.corresponding_author == profile:
                can_delete = True
            
            # Journal editors - can delete
            from apps.journals.models import JournalStaff
            if JournalStaff.objects.filter(
                journal=submission.journal, 
                profile=profile, 
                is_active=True
            ).exists():
                can_delete = True
        
        if not can_delete:
            return Response(
                {'error': 'You do not have permission to delete this document'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Delete the document (file will be deleted automatically via FileField)
        document.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
