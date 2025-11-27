"""
File management views for secure document handling.
Provides download, preview, and management endpoints.
"""
import os
from django.http import HttpResponse, Http404, FileResponse
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.db import models
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django_filters.rest_framework import DjangoFilterBackend

from apps.submissions.models import Document, DocumentVersion
from apps.submissions.serializers import DocumentSerializer, DocumentVersionSerializer
from .models import ActivityLog
from .serializers import ActivityLogSerializer
from .storage import SecureFileStorage, FileTypeDetector


class DocumentFilePermission(permissions.BasePermission):
    """
    Custom permissions for document file access.
    """
    
    def has_permission(self, request, view):
        """Check if user can access documents."""
        if not request.user.is_authenticated:
            return False
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access specific document."""
        # Author permissions
        if hasattr(obj, 'submission'):
            submission = obj.submission
            if request.user.profile == submission.corresponding_author:
                return True
            if request.user.profile in submission.coauthors.all():
                return True
        elif hasattr(obj, 'document'):
            submission = obj.document.submission
            if request.user.profile == submission.corresponding_author:
                return True
            if request.user.profile in submission.coauthors.all():
                return True
        
        # Journal staff permissions
        if hasattr(obj, 'submission'):
            journal = obj.submission.journal
        elif hasattr(obj, 'document'):
            journal = obj.document.submission.journal
        
        if journal.staff_members.filter(user=request.user, is_active=True).exists():
            return True
        
        # Admin permissions
        return request.user.is_staff or request.user.is_superuser


class FileManagementViewSet(viewsets.GenericViewSet):
    """
    ViewSet for file management operations.
    Handles secure file upload, download, and preview.
    """
    permission_classes = [DocumentFilePermission]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        summary="Upload document file",
        description="Upload a new file version for a document with validation and security checks.",
        parameters=[
            OpenApiParameter(
                name='document_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Document UUID"
            ),
        ],
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary'},
                    'change_summary': {'type': 'string', 'description': 'Summary of changes'},
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='upload/(?P<document_id>[^/.]+)')
    def upload_file(self, request, document_id=None):
        """Upload a new file version for a document."""
        try:
            document = get_object_or_404(Document, id=document_id)
            self.check_object_permissions(request, document)
            
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            uploaded_file = request.FILES['file']
            change_summary = request.data.get('change_summary', '')
            
            # Store file with validation
            try:
                storage_result = SecureFileStorage.store_file(
                    uploaded_file,
                    document.document_type,
                    document_id
                )
            except Exception as e:
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create new document version
            version_number = document.versions.count() + 1
            
            # Mark previous versions as not current
            document.versions.update(is_current=False)
            
            document_version = DocumentVersion.objects.create(
                document=document,
                version_number=version_number,
                change_summary=change_summary,
                file=storage_result['stored_path'],
                file_name=storage_result['original_name'],
                file_size=storage_result['file_size'],
                file_hash=storage_result['file_hash'],
                is_current=True,
                created_by=request.user.profile
            )
            
            # Update document's current version
            document.current_version = document_version
            document.save()
            
            serializer = DocumentVersionSerializer(document_version)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Upload failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Download document file",
        description="Download a specific document version with security checks.",
        parameters=[
            OpenApiParameter(
                name='version_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Document version UUID"
            ),
        ]
    )
    @action(detail=False, methods=['get'], url_path='download/(?P<version_id>[^/.]+)')
    def download_file(self, request, version_id=None):
        """Download a document file securely."""
        try:
            version = get_object_or_404(DocumentVersion, id=version_id)
            self.check_object_permissions(request, version)
            
            if not version.file or not default_storage.exists(version.file.name):
                raise Http404("File not found")
            
            # Get file
            file_path = version.file.path if hasattr(version.file, 'path') else version.file.name
            
            # Security check: ensure file is within allowed directory
            if not self._is_safe_path(file_path):
                raise Http404("File not found")
            
            # Open and serve file
            try:
                response = FileResponse(
                    default_storage.open(version.file.name, 'rb'),
                    as_attachment=True,
                    filename=version.file_name
                )
                
                # Set content type
                content_type = 'application/octet-stream'
                if hasattr(version.file, 'url'):
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(version.file_name)
                    if not content_type:
                        content_type = 'application/octet-stream'
                
                response['Content-Type'] = content_type
                response['Content-Length'] = version.file_size
                response['Content-Disposition'] = f'attachment; filename="{version.file_name}"'
                
                return response
                
            except Exception as e:
                raise Http404("File could not be accessed")
            
        except DocumentVersion.DoesNotExist:
            raise Http404("Document version not found")
    
    @extend_schema(
        summary="Preview document file",
        description="Preview a document file in browser (for supported formats).",
        parameters=[
            OpenApiParameter(
                name='version_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Document version UUID"
            ),
        ]
    )
    @action(detail=False, methods=['get'], url_path='preview/(?P<version_id>[^/.]+)')
    @method_decorator(cache_control(max_age=3600))  # Cache for 1 hour
    def preview_file(self, request, version_id=None):
        """Preview a document file in browser."""
        try:
            version = get_object_or_404(DocumentVersion, id=version_id)
            self.check_object_permissions(request, version)
            
            if not version.file or not default_storage.exists(version.file.name):
                raise Http404("File not found")
            
            # Check if file type supports preview
            previewable_types = [
                'application/pdf',
                'image/jpeg',
                'image/png',
                'image/gif',
                'text/plain',
            ]
            
            import mimetypes
            content_type, _ = mimetypes.guess_type(version.file_name)
            
            if content_type not in previewable_types:
                return Response(
                    {'error': 'File type not supported for preview'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Serve file for preview
            try:
                response = FileResponse(
                    default_storage.open(version.file.name, 'rb'),
                    content_type=content_type
                )
                response['Content-Length'] = version.file_size
                return response
                
            except Exception as e:
                raise Http404("File could not be accessed")
            
        except DocumentVersion.DoesNotExist:
            raise Http404("Document version not found")
    
    @extend_schema(
        summary="Get file information",
        description="Get metadata and information about a document file.",
        parameters=[
            OpenApiParameter(
                name='version_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Document version UUID"
            ),
        ]
    )
    @action(detail=False, methods=['get'], url_path='info/(?P<version_id>[^/.]+)')
    def file_info(self, request, version_id=None):
        """Get file information and metadata."""
        try:
            version = get_object_or_404(DocumentVersion, id=version_id)
            self.check_object_permissions(request, version)
            
            # Safely resolve creator display name
            try:
                if hasattr(version.created_by, 'get_full_name') and callable(getattr(version.created_by, 'get_full_name')):
                    created_by_name = version.created_by.get_full_name()
                else:
                    created_by_name = str(version.created_by)
            except Exception:
                created_by_name = str(getattr(version.created_by, 'user', 'Unknown'))

            # Basic file info
            file_info = {
                'id': version.id,
                'document_id': version.document.id,
                'version_number': version.version_number,
                'file_name': version.file_name,
                'file_size': version.file_size,
                'file_hash': version.file_hash,
                'created_at': version.created_at,
                'created_by': created_by_name,
                'is_current': version.is_current,
                'change_summary': version.change_summary,
            }
            
            # Add file type info
            import mimetypes
            content_type, encoding = mimetypes.guess_type(version.file_name)
            file_info['content_type'] = content_type
            file_info['encoding'] = encoding
            
            # Add download URL
            file_info['download_url'] = f"/api/v1/files/download/{version.id}"
            file_info['preview_url'] = f"/api/v1/files/preview/{version.id}"
            
            # Check if file exists
            file_info['file_exists'] = default_storage.exists(version.file.name) if version.file else False
            
            return Response(file_info)
            
        except DocumentVersion.DoesNotExist:
            raise Http404("Document version not found")
    
    @extend_schema(
        summary="Delete document file",
        description="Delete a document version and its associated file.",
        parameters=[
            OpenApiParameter(
                name='version_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Document version UUID"
            ),
        ]
    )
    @action(detail=False, methods=['delete'], url_path='delete/(?P<version_id>[^/.]+)')
    def delete_file(self, request, version_id=None):
        """Delete a document version and file."""
        try:
            version = get_object_or_404(DocumentVersion, id=version_id)
            self.check_object_permissions(request, version)
            
            # Check if this is the only version
            if version.document.versions.count() == 1:
                return Response(
                    {'error': 'Cannot delete the only version of a document'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if this is the current version
            if version.is_current:
                # Set the previous version as current
                previous_version = version.document.versions.exclude(id=version.id).first()
                if previous_version:
                    previous_version.is_current = True
                    previous_version.save()
                    version.document.current_version = previous_version
                    version.document.save()
            
            # Delete the file
            if version.file:
                SecureFileStorage.delete_file(version.file.name)
            
            # Delete the version record
            version.delete()
            
            return Response(
                {'message': 'File deleted successfully'}, 
                status=status.HTTP_204_NO_CONTENT
            )
            
        except DocumentVersion.DoesNotExist:
            raise Http404("Document version not found")
    
    def _is_safe_path(self, file_path):
        """
        Check if file path is safe and within allowed directories.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if path is safe
        """
        # Resolve absolute path
        abs_path = os.path.abspath(file_path)
        
        # Check if path is within media directory
        from django.conf import settings
        media_root = os.path.abspath(getattr(settings, 'MEDIA_ROOT', '/tmp'))
        return abs_path.startswith(media_root)


class DocumentVersionManagementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for document version management and history.
    """
    serializer_class = DocumentVersionSerializer
    permission_classes = [DocumentFilePermission]
    
    def get_queryset(self):
        """Get versions for documents user has access to."""
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return DocumentVersion.objects.all().select_related(
                'document__submission__journal',
                'created_by__user'
            )
        
        # Filter based on user's submissions and journal staff roles
        return DocumentVersion.objects.filter(
            models.Q(document__submission__corresponding_author=user.profile) |
            models.Q(document__submission__coauthors=user.profile) |
            models.Q(document__submission__journal__staff_members__user=user)
        ).select_related(
            'document__submission__journal',
            'created_by__user'
        ).distinct()
    
    @extend_schema(
        summary="Compare document versions",
        description="Compare two versions of a document to see changes.",
        parameters=[
            OpenApiParameter(
                name='version1_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="First version UUID"
            ),
            OpenApiParameter(
                name='version2_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Second version UUID"
            ),
        ]
    )
    @action(detail=False, methods=['get'])
    def compare(self, request):
        """Compare two document versions."""
        version1_id = request.query_params.get('version1_id')
        version2_id = request.query_params.get('version2_id')
        
        if not version1_id or not version2_id:
            return Response(
                {'error': 'Both version1_id and version2_id are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            version1 = get_object_or_404(DocumentVersion, id=version1_id)
            version2 = get_object_or_404(DocumentVersion, id=version2_id)
            
            self.check_object_permissions(request, version1)
            self.check_object_permissions(request, version2)
            
            # Basic comparison info
            comparison = {
                'version1': DocumentVersionSerializer(version1).data,
                'version2': DocumentVersionSerializer(version2).data,
                'changes': {
                    'file_size_change': version2.file_size - version1.file_size,
                    'time_difference': (version2.created_at - version1.created_at).total_seconds(),
                    'different_hash': version1.file_hash != version2.file_hash,
                }
            }
            
            # Add diff information if available
            if version2.diff_to_prev:
                comparison['diff'] = version2.diff_to_prev
            
            return Response(comparison)
            
        except DocumentVersion.DoesNotExist:
            return Response(
                {'error': 'One or both versions not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing system activity logs.
    
    Admin-only endpoint for monitoring all system events including:
    - User logins and logouts
    - Submission creation and updates
    - Review submissions and approvals
    - Publishing and withdrawal actions
    - And all other tracked system activities
    
    Provides comprehensive filtering and search capabilities.
    """
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'user': ['exact'],
        'action_type': ['exact', 'in'],
        'resource_type': ['exact', 'in'],
        'actor_type': ['exact', 'in'],
        'created_at': ['gte', 'lte', 'exact', 'date'],
        'ip_address': ['exact'],
    }
    search_fields = ['resource_id', 'metadata', 'user__email', 'user_agent']
    ordering_fields = ['created_at', 'action_type', 'resource_type']
    ordering = ['-created_at']  # Default ordering: newest first
    
    def get_queryset(self):
        """
        Get all activity logs.
        Only accessible by admin users (enforced by permission_classes).
        """
        return ActivityLog.objects.all().select_related('user').order_by('-created_at')
    
    @extend_schema(
        summary="List all system events",
        description="""
        Retrieve a paginated list of all system activity logs.
        
        **Filtering Options:**
        - `user`: Filter by user ID
        - `action_type`: Filter by action (LOGIN, SUBMIT, REVIEW, etc.)
        - `resource_type`: Filter by resource (USER, SUBMISSION, REVIEW, etc.)
        - `actor_type`: Filter by actor (USER, SYSTEM, API, INTEGRATION)
        - `created_at__gte`: Filter events after this date
        - `created_at__lte`: Filter events before this date
        - `ip_address`: Filter by IP address
        
        **Search:**
        Search across resource_id, metadata, user email, and user agent.
        
        **Ordering:**
        Order by created_at, action_type, or resource_type (prefix with - for descending).
        
        **Examples:**
        - Get all login events: `?action_type=LOGIN`
        - Get all submission events: `?resource_type=SUBMISSION`
        - Get events from specific user: `?user=<user_id>`
        - Get events in date range: `?created_at__gte=2025-11-01&created_at__lte=2025-11-30`
        - Search for specific resource: `?search=<resource_id>`
        """,
        parameters=[
            OpenApiParameter(
                name='user',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='Filter by user ID'
            ),
            OpenApiParameter(
                name='action_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by action type (LOGIN, SUBMIT, REVIEW, etc.)'
            ),
            OpenApiParameter(
                name='resource_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by resource type (USER, SUBMISSION, REVIEW, etc.)'
            ),
            OpenApiParameter(
                name='actor_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by actor type (USER, SYSTEM, API, INTEGRATION)'
            ),
            OpenApiParameter(
                name='created_at__gte',
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description='Filter events created after this date'
            ),
            OpenApiParameter(
                name='created_at__lte',
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description='Filter events created before this date'
            ),
            OpenApiParameter(
                name='ip_address',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by IP address'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in resource_id, metadata, user email, user agent'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order by field (prefix with - for descending). Options: created_at, action_type, resource_type'
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """List all activity logs with filtering and pagination."""
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary="Retrieve a specific activity log",
        description="Get detailed information about a specific system event by its ID."
    )
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific activity log entry."""
        return super().retrieve(request, *args, **kwargs)
