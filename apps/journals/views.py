"""
ViewSets for Journal management.
Handles journal CRUD operations, staff management, and configuration.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Journal, JournalStaff
from .serializers import (
    JournalSerializer, JournalListSerializer, JournalSettingsSerializer,
    JournalStaffSerializer, AddStaffMemberSerializer
)
from apps.users.models import Profile


class JournalPermissions(permissions.BasePermission):
    """
    Custom permissions for journal management.
    - Anyone can view active journals
    - Only staff/admin can create journals
    - Only journal staff can edit their journals
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (
            request.user.is_staff or
            request.user.is_superuser
        )
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for active journals
        if request.method in permissions.SAFE_METHODS:
            return obj.is_active or request.user.is_staff
        
        # Write permissions for journal staff or admin
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Check if user is journal staff
        if hasattr(request.user, 'profile'):
            return JournalStaff.objects.filter(
                journal=obj,
                profile=request.user.profile,
                is_active=True,
                role__in=['EDITOR_IN_CHIEF', 'MANAGING_EDITOR']
            ).exists()
        
        return False


class JournalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Journal management.
    
    Provides CRUD operations for journals with staff management.
    """
    queryset = Journal.objects.all()
    permission_classes = [JournalPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'short_name', 'description']
    ordering_fields = ['title', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return JournalListSerializer
        elif self.action in ['get_settings', 'update_settings']:
            return JournalSettingsSerializer
        return JournalSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = Journal.objects.select_related().prefetch_related(
            'staff_members__profile__user',
            'submissions'
        )
        
        # Non-staff users only see active journals
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @extend_schema(
        summary="Get journal settings",
        description="Retrieve journal-specific settings and configuration.",
    )
    @action(detail=True, methods=['get'])
    def get_settings(self, request, pk=None):
        """Get journal settings."""
        journal = self.get_object()
        serializer = JournalSettingsSerializer(journal)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Update journal settings",
        description="Update journal-specific settings and configuration.",
        request=JournalSettingsSerializer
    )
    @action(detail=True, methods=['put', 'patch'])
    def update_settings(self, request, pk=None):
        """Update journal settings."""
        journal = self.get_object()
        serializer = JournalSettingsSerializer(
            journal, 
            data=request.data, 
            partial=request.method == 'PATCH'
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="List journal staff",
        description="Get all staff members for a journal.",
        responses={200: JournalStaffSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def staff(self, request, pk=None):
        """Get journal staff members."""
        journal = self.get_object()
        staff = journal.staff_members.filter(is_active=True)
        serializer = JournalStaffSerializer(staff, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Add staff member",
        description="Add a new staff member to the journal.",
        request=AddStaffMemberSerializer,
        responses={201: JournalStaffSerializer}
    )
    @action(detail=True, methods=['post'])
    def add_staff(self, request, pk=None):
        """Add staff member to journal."""
        journal = self.get_object()
        serializer = AddStaffMemberSerializer(
            data=request.data,
            context={'journal': journal}
        )
        
        if serializer.is_valid():
            profile = serializer.validated_data['profile_id']
            role = serializer.validated_data['role']
            permissions_data = serializer.validated_data.get('permissions', {})
            
            staff_member = JournalStaff.objects.create(
                journal=journal,
                profile=profile,
                role=role,
                permissions=permissions_data
            )
            
            response_serializer = JournalStaffSerializer(staff_member)
            return Response(
                response_serializer.data, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Remove staff member",
        description="Remove a staff member from the journal (deactivate).",
        parameters=[
            OpenApiParameter(
                name='user_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Profile ID of the staff member to remove'
            )
        ]
    )
    @action(detail=True, methods=['delete'], url_path='staff/(?P<user_id>[^/.]+)')
    def remove_staff(self, request, pk=None, user_id=None):
        """Remove staff member from journal."""
        journal = self.get_object()
        profile = get_object_or_404(Profile, id=user_id)
        
        staff_member = get_object_or_404(
            JournalStaff,
            journal=journal,
            profile=profile,
            is_active=True
        )
        
        # Deactivate instead of delete for audit trail
        staff_member.is_active = False
        staff_member.save()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @extend_schema(
        summary="Update staff member",
        description="Update a staff member's role or permissions.",
        request=JournalStaffSerializer
    )
    @action(
        detail=True, 
        methods=['put', 'patch'], 
        url_path='staff/(?P<user_id>[^/.]+)/update'
    )
    def update_staff(self, request, pk=None, user_id=None):
        """Update staff member role or permissions."""
        journal = self.get_object()
        profile = get_object_or_404(Profile, id=user_id)

        staff_member = get_object_or_404(
            JournalStaff,
            journal=journal,
            profile=profile,
            is_active=True
        )

        serializer = JournalStaffSerializer(
            staff_member,
            data=request.data,
            partial=request.method == 'PATCH'
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Get journal statistics",
        description="Get statistics for a journal (submissions, reviews, etc.)."
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get journal statistics."""
        journal = self.get_object()
        
        stats = {
            'total_submissions': journal.submissions.count(),
            'active_submissions': journal.submissions.filter(
                status__in=['SUBMITTED', 'UNDER_REVIEW', 'REVISION_REQUIRED']
            ).count(),
            'published_articles': journal.submissions.filter(
                status='PUBLISHED'
            ).count(),
            'staff_count': journal.staff_members.filter(is_active=True).count(),
            'submission_stats': {
                status[0]: journal.submissions.filter(status=status[0]).count()
                for status in journal.submissions.model.STATUS_CHOICES
            }
        }
        
        return Response(stats)
