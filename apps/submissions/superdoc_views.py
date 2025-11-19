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

from .models import Submission, Document, AuthorContribution
from .superdoc_serializers import SuperDocCreateSerializer, SuperDocMetadataSerializer
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
        
        submission = document.submission
        
        # Corresponding author - full access
        if submission.corresponding_author == profile:
            return True
        
        # Co-authors - view only (edit check handled separately)
        if AuthorContribution.objects.filter(submission=submission, profile=profile).exists():
            # Allow GET requests (view)
            return request.method in permissions.SAFE_METHODS
        
        # Reviewers - view only
        if ReviewAssignment.objects.filter(submission=submission, reviewer=profile).exists():
            # Allow GET requests (view)
            return request.method in permissions.SAFE_METHODS
        
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
    
    # Corresponding author - full access
    if submission.corresponding_author == profile:
        return (True, True)
    
    # Co-authors - can view and comment (SuperDoc handles this in UI)
    if AuthorContribution.objects.filter(submission=submission, profile=profile).exists():
        return (True, False)
    
    # Reviewers - can view and comment (check review assignments)
    if ReviewAssignment.objects.filter(submission=submission, reviewer=profile).exists():
        return (True, False)
    
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
        description="Save the current DOCX file with all edits and comments embedded",
        responses={
            200: OpenApiResponse(description="Document saved successfully"),
            403: OpenApiResponse(description="No edit access to this document"),
            400: OpenApiResponse(description="No file provided"),
        }
    )
    @action(detail=True, methods=['post'], url_path='save')
    def save_document(self, request, pk=None):
        """
        Save document from SuperDoc editor.
        Frontend exports DOCX with all comments and sends it here.
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
        
        # Save the updated file
        document.original_file = docx_file
        document.file_name = docx_file.name
        document.file_size = docx_file.size
        document.last_edited_at = timezone.now()
        document.last_edited_by = request.user.profile
        document.save()
        
        # Return updated metadata
        serializer = SuperDocMetadataSerializer(document, context={'request': request})
        return Response({
            'status': 'saved',
            'message': 'Document saved successfully',
            'document': serializer.data
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
