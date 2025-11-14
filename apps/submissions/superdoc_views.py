"""
SuperDoc Integration ViewSet.
Minimal API for SuperDoc document editing - handles Yjs state and DOCX files only.
SuperDoc handles version history, comments, and tracked changes internally.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import FileResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse
import base64

from .models import Submission, Document
from .superdoc_serializers import SuperDocCreateSerializer, SuperDocMetadataSerializer
from apps.users.models import Profile


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
    
    # Corresponding author - full access
    if submission.corresponding_author == profile:
        return (True, True)
    
    # Co-authors - can view and comment (SuperDoc handles this in UI)
    from .models import AuthorContribution
    if AuthorContribution.objects.filter(submission=submission, profile=profile).exists():
        return (True, False)
    
    # Reviewers - can view and comment (check review assignments)
    from apps.reviews.models import ReviewAssignment
    if ReviewAssignment.objects.filter(submission=submission, reviewer=profile).exists():
        return (True, False)
    
    # Editors - full access
    journal = submission.journal
    if hasattr(journal, 'editorial_board'):
        if journal.editorial_board.filter(user=profile).exists():
            return (True, True)
    
    return (False, False)


class SuperDocViewSet(viewsets.ViewSet):
    """
    Minimal API for SuperDoc integration.
    
    SuperDoc handles:
    - Version history (via Yjs CRDT)
    - Comments and tracked changes
    - Collaborative editing UI
    
    Backend only handles:
    - Storing binary Yjs state
    - DOCX file upload/download
    - Access permissions
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """List all documents user has access to."""
        user = request.user
        profile = getattr(user, 'profile', None)
        
        if not profile:
            return Response([])
        
        # Get documents from user's submissions
        from .models import AuthorContribution
        
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
        
        serializer = SuperDocMetadataSerializer(documents, many=True)
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
                SuperDocMetadataSerializer(document).data,
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
        
        serializer = SuperDocMetadataSerializer(document)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Load document for SuperDoc editor",
        description="Returns document metadata, original DOCX URL, and Yjs state if exists",
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
        Returns original DOCX file URL + Yjs state if exists.
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
        
        # Add Yjs state if exists (base64 encoded binary data)
        if document.yjs_state:
            response_data['yjs_state'] = base64.b64encode(document.yjs_state).decode('utf-8')
        else:
            response_data['yjs_state'] = None
        
        return Response(response_data)
    
    @extend_schema(
        summary="Save Yjs state from SuperDoc",
        description="Save binary Yjs state containing document content, versions, and comments",
        responses={
            200: OpenApiResponse(description="State saved successfully"),
            403: OpenApiResponse(description="No edit access to this document"),
        }
    )
    @action(detail=True, methods=['post'], url_path='save-state')
    def save_state(self, request, pk=None):
        """
        Save Yjs state from SuperDoc.
        Called periodically by frontend to persist document state.
        """
        document = get_object_or_404(Document, pk=pk)
        can_view, can_edit = can_access_document(request.user, document)
        
        if not can_edit:
            return Response(
                {'error': 'You do not have permission to edit this document'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get base64 encoded Yjs state from request
        yjs_state_b64 = request.data.get('yjs_state')
        
        if yjs_state_b64:
            # Decode base64 to binary
            document.yjs_state = base64.b64decode(yjs_state_b64)
            document.last_edited_at = timezone.now()
            document.last_edited_by = request.user.profile
            document.save()
            
            return Response({
                'status': 'saved',
                'last_edited_at': document.last_edited_at
            })
        
        return Response(
            {'error': 'No yjs_state provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @extend_schema(
        summary="Upload DOCX file",
        description="Upload initial DOCX file for a new document",
        responses={
            200: OpenApiResponse(description="File uploaded successfully"),
            403: OpenApiResponse(description="No edit access to this document"),
        }
    )
    @action(detail=True, methods=['post'], url_path='upload')
    def upload_docx(self, request, pk=None):
        """
        Upload DOCX file to document.
        Used for initial upload or replacing the document.
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
        
        # Save file
        document.original_file = docx_file
        document.file_name = docx_file.name
        document.file_size = docx_file.size
        document.last_edited_at = timezone.now()
        document.last_edited_by = request.user.profile
        document.save()
        
        return Response({
            'status': 'uploaded',
            'file_name': document.file_name,
            'file_size': document.file_size,
            'file_url': request.build_absolute_uri(document.original_file.url)
        })
    
    @extend_schema(
        summary="Export document as DOCX",
        description="Save the current SuperDoc state as DOCX file",
        responses={
            200: OpenApiResponse(description="Document exported successfully"),
            403: OpenApiResponse(description="No edit access to this document"),
        }
    )
    @action(detail=True, methods=['post'], url_path='export')
    def export_docx(self, request, pk=None):
        """
        Export current document state to DOCX.
        Frontend sends the exported DOCX blob from SuperDoc.
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
        
        # Save as current version
        document.original_file = docx_file
        document.file_name = docx_file.name if docx_file.name else document.file_name
        document.file_size = docx_file.size
        document.last_edited_at = timezone.now()
        document.last_edited_by = request.user.profile
        document.save()
        
        return Response({
            'status': 'exported',
            'file_name': document.file_name,
            'file_url': request.build_absolute_uri(document.original_file.url)
        })
    
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
