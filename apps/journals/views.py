"""
ViewSets for Journal management.
Handles journal CRUD operations, staff management, and configuration.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
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
        # Read permissions - anyone can view any journal
        if request.method in permissions.SAFE_METHODS:
            return True
        
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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'short_name', 'description', 'issn_print', 'issn_online']
    filterset_fields = ['is_active', 'is_accepting_submissions']
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
        """Filter queryset based on user permissions and active role."""
        queryset = Journal.objects.select_related().prefetch_related(
            'staff_members__profile__user',
            'submissions'
        )
        
        # For detail view (retrieve), show all journals to authenticated users
        if self.action == 'retrieve':
            if self.request.user.is_authenticated:
                return queryset
            # Anonymous users can only see active journals
            return queryset.filter(is_active=True)
        
        # Superuser sees all journals
        if self.request.user.is_superuser:
            return queryset
        
        # Check for active role in request headers or query params
        active_role = self.request.headers.get('X-Active-Role') or self.request.query_params.get('active_role')
        
        # If user is explicitly acting as AUTHOR, show all active journals
        if active_role == 'AUTHOR':
            return queryset.filter(is_active=True, is_accepting_submissions=True)
        
        # Staff and Editors see only journals where they are staff members
        if self.request.user.is_staff or (hasattr(self.request.user, 'profile') and 
            self.request.user.profile.roles.filter(name='EDITOR').exists()):
            
            if hasattr(self.request.user, 'profile'):
                # Return only journals where this user is a staff member
                queryset = queryset.filter(
                    staff_members__profile=self.request.user.profile,
                    staff_members__is_active=True
                ).distinct()
                return queryset
        
        # Other users (including AUTHORS without explicit role header) see active journals
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
        summary="Configure OJS connection",
        description="Configure OJS (Open Journal Systems) connection for this journal. Requires Editor-in-Chief or Managing Editor role.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'ojs_api_url': {'type': 'string', 'format': 'uri', 'description': 'OJS API base URL'},
                    'ojs_api_key': {'type': 'string', 'description': 'OJS API key'},
                    'ojs_journal_id': {'type': 'integer', 'description': 'Journal ID in OJS system'},
                    'ojs_enabled': {'type': 'boolean', 'description': 'Enable OJS connection'}
                }
            }
        }
    )
    @action(detail=True, methods=['post', 'put'], url_path='ojs-connection', permission_classes=[IsAuthenticated])
    def configure_ojs(self, request, pk=None):
        """Configure OJS connection for this journal."""
        import requests
        
        journal = self.get_object()
        
        # Check if user has permission (Editor-in-Chief or Managing Editor)
        if hasattr(request.user, 'profile'):
            staff_member = journal.staff_members.filter(
                profile=request.user.profile,
                role__in=['EDITOR_IN_CHIEF', 'MANAGING_EDITOR'],
                is_active=True
            ).first()
            
            if not staff_member and not request.user.is_superuser:
                return Response(
                    {'detail': 'Only Editor-in-Chief or Managing Editor can configure OJS connection.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get the new OJS configuration from request
        ojs_api_url = request.data.get('ojs_api_url', journal.ojs_api_url)
        ojs_api_key = request.data.get('ojs_api_key', journal.ojs_api_key)
        ojs_journal_id = request.data.get('ojs_journal_id', journal.ojs_journal_id)
        ojs_enabled = request.data.get('ojs_enabled', journal.ojs_enabled)
        
        # Test connection before saving if credentials are provided
        if ojs_api_url and ojs_api_key:
            try:
                import logging
                logger = logging.getLogger(__name__)
                
                # Create a session to handle cookies (for bot detection)
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                })
                
                # Initialize session by visiting the site to get cookies
                import re
                import time
                try:
                    base_url = ojs_api_url.replace('/api/v1', '')
                    init_resp = session.get(base_url, timeout=10)
                    logger.info(f"Initial session response: status={init_resp.status_code}, cookies={len(session.cookies)}")
                    
                    # Check if we got a bot detection response
                    if init_resp.status_code == 409 or 'document.cookie' in init_resp.text:
                        logger.info("Bot detection triggered, extracting cookie...")
                        # Extract cookie from JavaScript: document.cookie = "humans_21909=1"
                        cookie_match = re.search(r'document\.cookie\s*=\s*"([^=]+)=([^"]+)"', init_resp.text)
                        if cookie_match:
                            cookie_name = cookie_match.group(1)
                            cookie_value = cookie_match.group(2)
                            logger.info(f"Setting bot detection cookie: {cookie_name}={cookie_value}")
                            session.cookies.set(cookie_name, cookie_value, domain=base_url.split('//')[1].split('/')[0])
                            
                            # Wait a moment then reload the page as the script expects
                            time.sleep(0.5)
                            init_resp = session.get(base_url, timeout=10)
                            logger.info(f"After cookie retry: status={init_resp.status_code}, cookies={len(session.cookies)}")
                    
                    logger.info(f"Session initialized successfully with {len(session.cookies)} cookies")
                except Exception as e:
                    logger.warning(f"Could not initialize session: {str(e)}")
                
                # First try: Bearer token with User-Agent to avoid WAF/ModSecurity blocks
                headers = {
                    'Authorization': f'Bearer {ojs_api_key}',
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                # Test connection with _context endpoint first (lightweight)
                test_url = f"{ojs_api_url}/_context"
                logger.info(f"Testing OJS connection to: {test_url}")
                
                response = session.get(test_url, headers=headers, timeout=10)
                
                # If _context not found, try submissions endpoint
                if response.status_code == 404:
                    test_url = f"{ojs_api_url}/submissions"
                    response = session.get(
                        test_url,
                        headers=headers,
                        params={'count': 1},
                        timeout=10
                    )
                
                logger.info(f"OJS response status: {response.status_code}")
                
                # If 406 from ModSecurity, try with minimal headers and apiToken parameter
                if response.status_code == 406 and 'Mod_Security' in response.text:
                    logger.info("ModSecurity block detected - trying with API token as query parameter")
                    # Some OJS instances accept API key as query parameter instead
                    minimal_headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/json'
                    }
                    response = session.get(
                        test_url,
                        headers=minimal_headers,
                        params={'apiToken': ojs_api_key, 'count': 1},
                        timeout=10
                    )
                    logger.info(f"Query parameter attempt status: {response.status_code}")
                
                # If still 406, try alternative header format
                if response.status_code == 406:
                    logger.info("Trying alternative header format with X-Csrf-Token")
                    headers_alt = {
                        'X-Csrf-Token': ojs_api_key,
                        'Accept': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    response = session.get(test_url, headers=headers_alt, timeout=10)
                    logger.info(f"Alternative attempt status: {response.status_code}")
                
                if response.status_code == 401:
                    return Response({
                        'detail': 'Authentication failed - invalid API key',
                        'error': 'invalid_credentials'
                    }, status=status.HTTP_400_BAD_REQUEST)
                elif response.status_code == 403:
                    return Response({
                        'detail': 'Access forbidden - insufficient permissions',
                        'error': 'forbidden'
                    }, status=status.HTTP_400_BAD_REQUEST)
                elif response.status_code == 406:
                    # Check if it's ModSecurity blocking
                    if 'Mod_Security' in response.text or 'ModSecurity' in response.text:
                        logger.error(f"ModSecurity blocking request")
                        return Response({
                            'detail': 'Request blocked by server firewall (ModSecurity). The OJS server security configuration is preventing API access. Contact the OJS administrator to whitelist API requests.',
                            'error': 'firewall_blocked',
                            'suggestion': 'Ask the OJS administrator to configure ModSecurity to allow REST API requests with Bearer tokens.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        logger.error(f"406 response body: {response.text[:500]}")
                        return Response({
                            'detail': f'OJS server returned 406 Not Acceptable. Response: {response.text[:200]}',
                            'error': 'not_acceptable',
                            'suggestion': 'This OJS instance may have different API configuration. Check OJS version and API settings.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                elif response.status_code == 404:
                    return Response({
                        'detail': 'OJS API endpoint not found - verify the API URL is correct',
                        'error': 'endpoint_not_found'
                    }, status=status.HTTP_400_BAD_REQUEST)
                elif response.status_code != 200:
                    # Include response text for debugging
                    error_detail = response.text[:300] if response.text else 'No error details'
                    logger.error(f"OJS connection failed: {response.status_code} - {error_detail}")
                    return Response({
                        'detail': f'Connection failed with status {response.status_code}',
                        'error': 'connection_failed',
                        'response_body': error_detail
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Connection successful
                logger.info("OJS connection successful")
                
            except requests.exceptions.Timeout:
                return Response({
                    'detail': 'Connection timeout - OJS server not responding',
                    'error': 'timeout'
                }, status=status.HTTP_400_BAD_REQUEST)
            except requests.exceptions.ConnectionError:
                return Response({
                    'detail': 'Cannot reach OJS server - check URL and network',
                    'error': 'connection_error'
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    'detail': f'Connection error: {str(e)}',
                    'error': 'unknown_error'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update OJS settings after successful connection test
        journal.ojs_enabled = ojs_enabled
        journal.ojs_api_url = ojs_api_url
        journal.ojs_api_key = ojs_api_key
        journal.ojs_journal_id = ojs_journal_id
        
        journal.save()
        
        return Response({
            'detail': 'OJS connection configured successfully',
            'ojs_enabled': journal.ojs_enabled,
            'ojs_api_url': journal.ojs_api_url,
            'ojs_journal_id': journal.ojs_journal_id
        })
    
    @extend_schema(
        summary="Get OJS connection status",
        description="Get current OJS connection configuration and status."
    )
    @action(detail=True, methods=['get'], url_path='ojs-status')
    def ojs_status(self, request, pk=None):
        """Get OJS connection status."""
        journal = self.get_object()
        
        return Response({
            'ojs_enabled': journal.ojs_enabled,
            'ojs_configured': bool(journal.ojs_api_url and journal.ojs_api_key),
            'ojs_api_url': journal.ojs_api_url if journal.ojs_enabled else None,
            'ojs_journal_id': journal.ojs_journal_id if journal.ojs_enabled else None
        })
    
    @extend_schema(
        summary="Test OJS connection",
        description="Test the OJS API connection with current credentials."
    )
    @action(detail=True, methods=['post'], url_path='test-ojs-connection', permission_classes=[IsAuthenticated])
    def test_ojs_connection(self, request, pk=None):
        """Test OJS connection."""
        journal = self.get_object()
        
        if not journal.ojs_enabled or not journal.ojs_api_url or not journal.ojs_api_key:
            return Response(
                {'detail': 'OJS connection not configured'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.integrations.utils import ojs_list_journals
            result = ojs_list_journals(journal.ojs_api_url, journal.ojs_api_key)
            
            return Response({
                'success': True,
                'message': 'OJS connection successful',
                'journals_found': len(result.get('items', result if isinstance(result, list) else []))
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'OJS connection failed: {str(e)}'
            }, status=status.HTTP_502_BAD_GATEWAY)
    
    @extend_schema(
        summary="Disconnect OJS",
        description="Disable and clear OJS connection for this journal."
    )
    @action(detail=True, methods=['post'], url_path='disconnect-ojs', permission_classes=[IsAuthenticated])
    def disconnect_ojs(self, request, pk=None):
        """Disconnect OJS."""
        journal = self.get_object()
        
        # Check permission
        if hasattr(request.user, 'profile'):
            staff_member = journal.staff_members.filter(
                profile=request.user.profile,
                role__in=['EDITOR_IN_CHIEF', 'MANAGING_EDITOR'],
                is_active=True
            ).first()
            
            if not staff_member and not request.user.is_superuser:
                return Response(
                    {'detail': 'Only Editor-in-Chief or Managing Editor can disconnect OJS.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Clear OJS settings
        journal.ojs_enabled = False
        journal.ojs_api_url = ''
        journal.ojs_api_key = ''
        journal.ojs_journal_id = None
        journal.save()
        
        return Response({'detail': 'OJS disconnected successfully'})
    
    @action(detail=True, methods=['post'], url_path='import-from-ojs', permission_classes=[IsAuthenticated])
    def import_from_ojs(self, request, pk=None):
        """
        Import all data from OJS into Django database.
        This imports users first, then submissions with proper author links.
        Runs as a background task to avoid request timeout.
        """
        journal = self.get_object()
        
        # Check permission
        if hasattr(request.user, 'profile'):
            staff_member = journal.staff_members.filter(
                profile=request.user.profile,
                role__in=['EDITOR_IN_CHIEF', 'MANAGING_EDITOR'],
                is_active=True
            ).first()
            
            if not staff_member and not request.user.is_superuser:
                return Response(
                    {'detail': 'Only Editor-in-Chief or Managing Editor can import from OJS.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Check OJS configuration
        if not journal.ojs_api_url or not journal.ojs_api_key:
            return Response(
                {'detail': 'OJS is not configured for this journal.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if import is already in progress
        from django.core.cache import cache
        progress_key = f"ojs_import_progress_{journal.id}"
        existing_progress = cache.get(progress_key)
        
        if existing_progress and existing_progress.get('status') in ['fetching', 'processing']:
            return Response({
                'detail': 'Import is already in progress',
                'progress': existing_progress
            }, status=status.HTTP_409_CONFLICT)
        
        # Start import in background thread
        import threading
        
        def run_import():
            try:
                from apps.integrations.ojs_sync import import_all_ojs_data_for_journal
                import_all_ojs_data_for_journal(journal)
            except Exception as e:
                # Update cache with error status
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Background OJS import failed: {str(e)}")
                
                progress = cache.get(progress_key, {})
                progress['status'] = 'failed'
                progress['error'] = str(e)
                cache.set(progress_key, progress, timeout=3600)
        
        # Start background thread
        thread = threading.Thread(target=run_import, daemon=True)
        thread.start()
        
        return Response({
            'detail': 'OJS import started in background',
            'message': 'Use the import-progress endpoint to check status',
            'progress_endpoint': f'/api/v1/journals/journals/{journal.id}/import-progress/'
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['get'], url_path='import-progress', permission_classes=[IsAuthenticated])
    def import_progress(self, request, pk=None):
        """
        Get the current progress of OJS import operation.
        Returns progress information including current item, total items, and status.
        """
        from django.core.cache import cache
        
        journal = self.get_object()
        
        # Check permission
        if hasattr(request.user, 'profile'):
            staff_member = journal.staff_members.filter(
                profile=request.user.profile,
                is_active=True
            ).first()
            
            if not staff_member and not request.user.is_superuser:
                return Response(
                    {'detail': 'You do not have permission to view import progress.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get progress from cache
        progress_key = f"ojs_import_progress_{journal.id}"
        progress = cache.get(progress_key)
        
        if not progress:
            return Response({
                'status': 'idle',
                'message': 'No import in progress'
            })
        
        return Response(progress)
    
    @action(detail=True, methods=['get', 'post'], url_path='verification-requests', permission_classes=[IsAuthenticated])
    def verification_requests(self, request, pk=None):
        """
        Get or manage verification requests for users imported from this journal.
        Editors can view and approve/reject verification requests for users imported from their journal.
        """
        from apps.users.models import VerificationRequest, CustomUser
        from apps.users.verification_serializers import VerificationRequestDetailSerializer
        from django.utils import timezone
        
        journal = self.get_object()
        
        # Check permission - must be editor of this journal
        if hasattr(request.user, 'profile'):
            staff_member = journal.staff_members.filter(
                profile=request.user.profile,
                role__in=['EDITOR_IN_CHIEF', 'MANAGING_EDITOR'],
                is_active=True
            ).first()
            
            if not staff_member and not request.user.is_superuser:
                return Response(
                    {'detail': 'Only Editor-in-Chief or Managing Editor can manage verification requests.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        if request.method == 'GET':
            # Get all users imported from this journal
            imported_users = CustomUser.objects.filter(imported_from=journal.id)
            
            # Get verification requests for these users
            verification_requests = VerificationRequest.objects.filter(
                profile__user__in=imported_users
            ).select_related('profile', 'profile__user', 'reviewed_by')
            
            # Optional status filter
            status_param = request.query_params.get('status')
            if status_param:
                verification_requests = verification_requests.filter(status=status_param)
            
            serializer = VerificationRequestDetailSerializer(verification_requests, many=True)
            return Response({
                'journal': {
                    'id': str(journal.id),
                    'title': journal.title
                },
                'total_imported_users': imported_users.count(),
                'verification_requests': serializer.data
            })
        
        return Response(
            {'detail': 'Method not allowed'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    @action(detail=True, methods=['post'], url_path='verification-requests/(?P<request_id>[^/.]+)/approve', permission_classes=[IsAuthenticated])
    def approve_verification(self, request, pk=None, request_id=None):
        """
        Approve a verification request for a user imported from this journal.
        """
        from apps.users.models import VerificationRequest, CustomUser, Role
        from apps.users.verification_serializers import VerificationReviewSerializer
        from django.utils import timezone
        
        journal = self.get_object()
        
        # Check permission
        if hasattr(request.user, 'profile'):
            staff_member = journal.staff_members.filter(
                profile=request.user.profile,
                role__in=['EDITOR_IN_CHIEF', 'MANAGING_EDITOR'],
                is_active=True
            ).first()
            
            if not staff_member and not request.user.is_superuser:
                return Response(
                    {'detail': 'Only Editor-in-Chief or Managing Editor can approve verification requests.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get verification request
        try:
            verification_request = VerificationRequest.objects.get(id=request_id)
        except VerificationRequest.DoesNotExist:
            return Response(
                {'detail': 'Verification request not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check that the user was imported from this journal
        if verification_request.profile.user.imported_from != journal.id:
            return Response(
                {'detail': 'This verification request is not for a user imported from your journal.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check status
        if verification_request.status not in ['PENDING', 'INFO_REQUESTED']:
            return Response(
                {'detail': 'Can only approve pending or info_requested requests'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VerificationReviewSerializer(data=request.data)
        if serializer.is_valid():
            # Update verification request
            verification_request.status = 'APPROVED'
            verification_request.reviewed_by = request.user
            verification_request.reviewed_at = timezone.now()
            verification_request.admin_notes = serializer.validated_data.get('admin_notes', '')
            verification_request.save()
            
            # Update profile verification status
            profile = verification_request.profile
            profile.verification_status = 'GENUINE'
            
            # Add requested roles
            granted_roles = []
            
            for role_name in verification_request.requested_roles:
                if role_name == 'AUTHOR':
                    author_role, _ = Role.objects.get_or_create(name='AUTHOR')
                    profile.roles.add(author_role)
                    granted_roles.append('Author')
                elif role_name == 'REVIEWER':
                    reviewer_role, _ = Role.objects.get_or_create(name='REVIEWER')
                    profile.roles.add(reviewer_role)
                    granted_roles.append('Reviewer')
                elif role_name == 'EDITOR':
                    editor_role, _ = Role.objects.get_or_create(name='EDITOR')
                    profile.roles.add(editor_role)
                    granted_roles.append('Editor')
            
            profile.save()
            
            return Response({
                'detail': 'Verification approved',
                'profile_status': profile.verification_status,
                'roles_granted': granted_roles
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='verification-requests/(?P<request_id>[^/.]+)/reject', permission_classes=[IsAuthenticated])
    def reject_verification(self, request, pk=None, request_id=None):
        """
        Reject a verification request for a user imported from this journal.
        """
        from apps.users.models import VerificationRequest, CustomUser
        from apps.users.verification_serializers import VerificationReviewSerializer
        from django.utils import timezone
        
        journal = self.get_object()
        
        # Check permission
        if hasattr(request.user, 'profile'):
            staff_member = journal.staff_members.filter(
                profile=request.user.profile,
                role__in=['EDITOR_IN_CHIEF', 'MANAGING_EDITOR'],
                is_active=True
            ).first()
            
            if not staff_member and not request.user.is_superuser:
                return Response(
                    {'detail': 'Only Editor-in-Chief or Managing Editor can reject verification requests.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get verification request
        try:
            verification_request = VerificationRequest.objects.get(id=request_id)
        except VerificationRequest.DoesNotExist:
            return Response(
                {'detail': 'Verification request not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check that the user was imported from this journal
        if verification_request.profile.user.imported_from != journal.id:
            return Response(
                {'detail': 'This verification request is not for a user imported from your journal.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check status
        if verification_request.status not in ['PENDING', 'INFO_REQUESTED']:
            return Response(
                {'detail': 'Can only reject pending or info_requested requests'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VerificationReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        rejection_reason = serializer.validated_data.get('rejection_reason')
        if not rejection_reason:
            return Response(
                {'detail': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update verification request
        verification_request.status = 'REJECTED'
        verification_request.reviewed_by = request.user
        verification_request.reviewed_at = timezone.now()
        verification_request.rejection_reason = rejection_reason
        verification_request.admin_notes = serializer.validated_data.get('admin_notes', '')
        verification_request.save()
        
        # Update profile verification status
        profile = verification_request.profile
        profile.verification_status = 'SUSPICIOUS'
        profile.save()
        
        return Response({
            'detail': 'Verification rejected',
            'profile_status': profile.verification_status
        })
    
    @action(detail=True, methods=['post'], url_path='verification-requests/(?P<request_id>[^/.]+)/request-info', permission_classes=[IsAuthenticated])
    def request_verification_info(self, request, pk=None, request_id=None):
        """
        Request additional information for a verification request.
        """
        from apps.users.models import VerificationRequest, CustomUser
        from django.utils import timezone
        
        journal = self.get_object()
        
        # Check permission
        if hasattr(request.user, 'profile'):
            staff_member = journal.staff_members.filter(
                profile=request.user.profile,
                role__in=['EDITOR_IN_CHIEF', 'MANAGING_EDITOR'],
                is_active=True
            ).first()
            
            if not staff_member and not request.user.is_superuser:
                return Response(
                    {'detail': 'Only Editor-in-Chief or Managing Editor can request additional information.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get verification request
        try:
            verification_request = VerificationRequest.objects.get(id=request_id)
        except VerificationRequest.DoesNotExist:
            return Response(
                {'detail': 'Verification request not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check that the user was imported from this journal
        if verification_request.profile.user.imported_from != journal.id:
            return Response(
                {'detail': 'This verification request is not for a user imported from your journal.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check status
        if verification_request.status != 'PENDING':
            return Response(
                {'detail': 'Can only request additional info for pending requests'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        info_request = request.data.get('info_request')
        if not info_request:
            return Response(
                {'detail': 'info_request field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update verification request
        verification_request.status = 'INFO_REQUESTED'
        verification_request.additional_info_requested = info_request
        verification_request.reviewed_by = request.user
        verification_request.reviewed_at = timezone.now()
        verification_request.save()
        
        return Response({
            'detail': 'Additional information requested',
            'status': verification_request.status
        })
    
    @extend_schema(
        summary="Get journals where user is editor",
        description="Get all journals where the current user is a staff member (editor)."
    )
    @action(detail=False, methods=['get'], url_path='assigned-journals', permission_classes=[IsAuthenticated])
    def my_editor_journals(self, request):
        """Get all journals where the current user is a staff member."""
        if not hasattr(request.user, 'profile'):
            return Response(
                {'detail': 'User profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get journals where user is an active staff member
        journals = Journal.objects.filter(
            staff_members__profile=request.user.profile,
            staff_members__is_active=True
        ).distinct().select_related().prefetch_related('staff_members__profile__user')
        
        # Optional role filter
        role = request.query_params.get('role')
        if role:
            journals = journals.filter(staff_members__role=role)
        
        serializer = JournalListSerializer(journals, many=True)
        return Response(serializer.data)
    
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
