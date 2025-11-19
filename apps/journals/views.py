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

from .models import Journal, JournalStaff, Section, Category, ResearchType, Area
from .serializers import (
    JournalSerializer, JournalListSerializer, JournalSettingsSerializer,
    JournalStaffSerializer, AddStaffMemberSerializer,
    SectionSerializer, CategorySerializer, ResearchTypeSerializer,
    AreaSerializer, TaxonomyTreeSerializer
)
from apps.users.models import Profile


class JournalPermissions(permissions.BasePermission):
    """
    Custom permissions for journal management.
    - Anyone can view active journals
    - Users with EDITOR role, staff, or admin can create journals
    - Only journal staff can edit their journals
    - Editors (Editor-in-Chief, Managing Editor) can manage staff
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Special handling for staff management actions
        if view.action in ['add_staff', 'remove_staff', 'update_staff']:
            return request.user.is_authenticated
        
        # Allow authenticated users with EDITOR role to create/modify journals
        if not request.user.is_authenticated:
            return False
        
        # Superuser and staff always have permission
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user has EDITOR role
        if hasattr(request.user, 'profile'):
            from apps.users.models import Role
            return request.user.profile.roles.filter(name='EDITOR').exists()
        
        return False
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for active journals
        if request.method in permissions.SAFE_METHODS:
            return obj.is_active or request.user.is_staff
        
        # Write permissions for journal staff or admin
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Check if user is journal editor with management permissions
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
    
    def perform_create(self, serializer):
        """Create journal and automatically add creator as Editor-in-Chief."""
        journal = serializer.save()
        
        # Automatically add the creator as Editor-in-Chief if they have a profile
        if hasattr(self.request.user, 'profile'):
            JournalStaff.objects.create(
                journal=journal,
                profile=self.request.user.profile,
                role='EDITOR_IN_CHIEF',
                is_active=True
            )
    
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
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_staff(self, request, pk=None):
        """Add staff member to journal. Requires Editor-in-Chief or Managing Editor role."""
        journal = self.get_object()
        
        # Check if user has permission to add staff
        if not (request.user.is_superuser or request.user.is_staff):
            if not hasattr(request.user, 'profile'):
                return Response(
                    {'detail': 'You do not have permission to perform this action.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if user is Editor-in-Chief or Managing Editor
            is_editor = JournalStaff.objects.filter(
                journal=journal,
                profile=request.user.profile,
                is_active=True,
                role__in=['EDITOR_IN_CHIEF', 'MANAGING_EDITOR']
            ).exists()
            
            if not is_editor:
                return Response(
                    {'detail': 'Only Editor-in-Chief or Managing Editor can add staff members.'},
                    status=status.HTTP_403_FORBIDDEN
                )
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
    @action(detail=True, methods=['delete'], url_path='staff/(?P<user_id>[^/.]+)', permission_classes=[IsAuthenticated])
    def remove_staff(self, request, pk=None, user_id=None):
        """Remove staff member from journal. Requires Editor-in-Chief or Managing Editor role."""
        journal = self.get_object()
        
        # Check if user has permission to remove staff
        if not (request.user.is_superuser or request.user.is_staff):
            if not hasattr(request.user, 'profile'):
                return Response(
                    {'detail': 'You do not have permission to perform this action.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            is_editor = JournalStaff.objects.filter(
                journal=journal,
                profile=request.user.profile,
                is_active=True,
                role__in=['EDITOR_IN_CHIEF', 'MANAGING_EDITOR']
            ).exists()
            
            if not is_editor:
                return Response(
                    {'detail': 'Only Editor-in-Chief or Managing Editor can remove staff members.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
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
        url_path='staff/(?P<user_id>[^/.]+)/update',
        permission_classes=[IsAuthenticated]
    )
    def update_staff(self, request, pk=None, user_id=None):
        """Update staff member role or permissions. Requires Editor-in-Chief or Managing Editor role."""
        journal = self.get_object()
        
        # Check if user has permission to update staff
        if not (request.user.is_superuser or request.user.is_staff):
            if not hasattr(request.user, 'profile'):
                return Response(
                    {'detail': 'You do not have permission to perform this action.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            is_editor = JournalStaff.objects.filter(
                journal=journal,
                profile=request.user.profile,
                is_active=True,
                role__in=['EDITOR_IN_CHIEF', 'MANAGING_EDITOR']
            ).exists()
            
            if not is_editor:
                return Response(
                    {'detail': 'Only Editor-in-Chief or Managing Editor can update staff members.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
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


class SectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Section management.
    Provides CRUD operations for journal sections.
    """
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['order', 'name', 'created_at']
    ordering = ['order', 'name']
    
    def get_queryset(self):
        """Filter sections by journal."""
        queryset = Section.objects.select_related('journal', 'section_editor').prefetch_related('categories')
        
        # Filter by journal if provided
        journal_id = self.request.query_params.get('journal')
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        
        # Non-staff users only see active sections
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(is_active=True)
        
        return queryset


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category management.
    Provides CRUD operations for categories within sections.
    """
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['order', 'name', 'created_at']
    ordering = ['order', 'name']
    
    def get_queryset(self):
        """Filter categories by section or journal."""
        queryset = Category.objects.select_related('section__journal').prefetch_related('research_types')
        
        # Filter by section if provided
        section_id = self.request.query_params.get('section')
        if section_id:
            queryset = queryset.filter(section_id=section_id)
        
        # Filter by journal if provided
        journal_id = self.request.query_params.get('journal')
        if journal_id:
            queryset = queryset.filter(section__journal_id=journal_id)
        
        # Non-staff users only see active categories
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(is_active=True)
        
        return queryset


class ResearchTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ResearchType management.
    Provides CRUD operations for research types within categories.
    """
    serializer_class = ResearchTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['order', 'name', 'created_at']
    ordering = ['order', 'name']
    
    def get_queryset(self):
        """Filter research types by category, section, or journal."""
        queryset = ResearchType.objects.select_related('category__section__journal').prefetch_related('areas')
        
        # Filter by category if provided
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by section if provided
        section_id = self.request.query_params.get('section')
        if section_id:
            queryset = queryset.filter(category__section_id=section_id)
        
        # Filter by journal if provided
        journal_id = self.request.query_params.get('journal')
        if journal_id:
            queryset = queryset.filter(category__section__journal_id=journal_id)
        
        # Non-staff users only see active research types
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(is_active=True)
        
        return queryset


class AreaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Area management.
    Provides CRUD operations for areas within research types.
    """
    serializer_class = AreaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description', 'keywords']
    ordering_fields = ['order', 'name', 'created_at']
    ordering = ['order', 'name']
    
    def get_queryset(self):
        """Filter areas by research type, category, section, or journal."""
        queryset = Area.objects.select_related('research_type__category__section__journal')
        
        # Filter by research type if provided
        research_type_id = self.request.query_params.get('research_type')
        if research_type_id:
            queryset = queryset.filter(research_type_id=research_type_id)
        
        # Filter by category if provided
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(research_type__category_id=category_id)
        
        # Filter by section if provided
        section_id = self.request.query_params.get('section')
        if section_id:
            queryset = queryset.filter(research_type__category__section_id=section_id)
        
        # Filter by journal if provided
        journal_id = self.request.query_params.get('journal')
        if journal_id:
            queryset = queryset.filter(research_type__category__section__journal_id=journal_id)
        
        # Non-staff users only see active areas
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @extend_schema(
        summary="Get complete taxonomy tree for a journal",
        description="Returns nested structure: Section -> Category -> ResearchType -> Area",
        parameters=[
            OpenApiParameter(
                name='journal_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='Journal ID to get taxonomy tree for',
                required=True
            )
        ]
    )
    @action(detail=False, methods=['get'], url_path='taxonomy-tree')
    def taxonomy_tree(self, request):
        """Get complete taxonomy tree for a journal."""
        journal_id = request.query_params.get('journal_id')
        
        if not journal_id:
            return Response(
                {'error': 'journal_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sections = Section.objects.filter(
            journal_id=journal_id,
            is_active=True
        ).prefetch_related(
            'categories__research_types__areas'
        )
        
        serializer = TaxonomyTreeSerializer(sections, many=True)
        return Response(serializer.data)
