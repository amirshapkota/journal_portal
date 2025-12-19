"""
Serializers for Journal management.
Handles journal CRUD, staff management, and configuration.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Journal, JournalStaff, Section, Category, ResearchType, Area
from apps.users.serializers import ProfileSerializer

User = get_user_model()


class JournalStaffSerializer(serializers.ModelSerializer):
    """Serializer for Journal Staff management."""
    
    profile = ProfileSerializer(read_only=True)
    profile_id = serializers.UUIDField(write_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = JournalStaff
        fields = (
            'id', 'profile', 'profile_id', 'role', 'role_display',
            'is_active', 'start_date', 'end_date', 'permissions',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def validate_profile_id(self, value):
        """Validate that profile exists."""
        from apps.users.models import Profile
        try:
            Profile.objects.get(id=value)
        except Profile.DoesNotExist:
            raise serializers.ValidationError("Profile does not exist.")
        return value


class JournalSerializer(serializers.ModelSerializer):
    """Comprehensive Journal serializer."""
    
    staff_members = JournalStaffSerializer(many=True, read_only=True)
    submission_count = serializers.SerializerMethodField()
    active_staff_count = serializers.SerializerMethodField()
    ojs_connection_status = serializers.SerializerMethodField()
    editor_in_chief_email = serializers.EmailField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Journal
        fields = (
            'id', 'title', 'short_name', 'publisher', 'description',
            'issn_print', 'issn_online', 'website_url', 'contact_email',
            'main_contact_name', 'main_contact_email', 'main_contact_phone',
            'technical_contact_name', 'technical_contact_email', 'technical_contact_phone',
            'settings', 'is_active', 'is_accepting_submissions',
            'staff_members', 'submission_count', 'active_staff_count',
            'ojs_connection_status', 'editor_in_chief_email',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_submission_count(self, obj):
        """Get total submission count for this journal."""
        return obj.submissions.count()
    
    def get_active_staff_count(self, obj):
        """Get active staff member count."""
        return obj.staff_members.filter(is_active=True).count()
    
    def get_ojs_connection_status(self, obj):
        """
        Get OJS connection status for this journal.
        Returns configuration status and connection health.
        """
        import requests
        import re
        import time
        
        status = {
            'configured': False,
            'connected': False,
            'api_url': None,
            'journal_id': None,
            'error': None
        }
        
        # Check if OJS is configured
        if not obj.ojs_api_url or not obj.ojs_api_key:
            status['error'] = 'OJS not configured'
            return status
        
        status['configured'] = True
        status['api_url'] = obj.ojs_api_url
        status['journal_id'] = obj.ojs_journal_id
        
        # Test connection by making a simple API call
        try:
            # Create a session to handle cookies (for bot detection)
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            })
            
            # Initialize session by visiting the site to get cookies
            try:
                base_url = obj.ojs_api_url.replace('/api/v1', '')
                init_resp = session.get(base_url, timeout=5)
                
                # Check if we got a bot detection response
                if init_resp.status_code == 409 or 'document.cookie' in init_resp.text:
                    # Extract cookie from JavaScript: document.cookie = "humans_21909=1"
                    cookie_match = re.search(r'document\.cookie\s*=\s*"([^=]+)=([^"]+)"', init_resp.text)
                    if cookie_match:
                        cookie_name = cookie_match.group(1)
                        cookie_value = cookie_match.group(2)
                        session.cookies.set(cookie_name, cookie_value, domain=base_url.split('//')[1].split('/')[0])
                        
                        # Wait a moment then reload
                        time.sleep(0.3)
                        init_resp = session.get(base_url, timeout=5)
            except Exception:
                pass  # Continue even if initialization fails
            
            headers = {
                'Authorization': f'Bearer {obj.ojs_api_key}',
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # Try _context endpoint first (lightweight)
            response = session.get(
                f"{obj.ojs_api_url}/_context",
                headers=headers,
                timeout=5
            )
            
            # If _context not found, try submissions endpoint
            if response.status_code == 404:
                response = session.get(
                    f"{obj.ojs_api_url}/submissions",
                    headers=headers,
                    params={'count': 1},
                    timeout=5
                )
            
            # If 406, try alternative header format
            if response.status_code == 406:
                headers_alt = {
                    'X-Csrf-Token': obj.ojs_api_key,
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = session.get(
                    f"{obj.ojs_api_url}/submissions",
                    headers=headers_alt,
                    params={'count': 1},
                    timeout=5
                )
            
            if response.status_code == 200:
                status['connected'] = True
            elif response.status_code == 401:
                status['error'] = 'Authentication failed - invalid API key'
            elif response.status_code == 403:
                status['error'] = 'Access forbidden - insufficient permissions'
            elif response.status_code == 404:
                status['error'] = 'OJS endpoint not found'
            elif response.status_code == 406:
                if 'Mod_Security' in response.text or 'ModSecurity' in response.text:
                    status['error'] = 'Blocked by server firewall (ModSecurity)'
                else:
                    status['error'] = 'OJS API version mismatch'
            else:
                status['error'] = f'Connection failed with status {response.status_code}'
        except requests.exceptions.Timeout:
            status['error'] = 'Connection timeout'
        except requests.exceptions.ConnectionError:
            status['error'] = 'Cannot reach OJS server'
        except Exception as e:
            status['error'] = f'Connection error: {str(e)}'
        
        return status
    
    def validate_short_name(self, value):
        """Validate short name is unique and properly formatted."""
        # Allow alphanumeric and hyphens only
        import re
        if not re.match(r'^[a-zA-Z0-9-]+$', value):
            raise serializers.ValidationError(
                "Short name can only contain letters, numbers, and hyphens."
            )
        return value.upper()  # Store in uppercase for consistency
    
    def validate_issn_print(self, value):
        """Validate ISSN format."""
        if value:
            import re
            if not re.match(r'^[A-Za-z0-9]{4}-[A-Za-z0-9]{4}$', value):
                raise serializers.ValidationError(
                    "ISSN must be in format: 1234-5678"
                )
        return value
    
    def validate_issn_online(self, value):
        """Validate online ISSN format."""
        if value:
            import re
            if not re.match(r'^[A-Za-z0-9]{4}-[A-Za-z0-9]{4}$', value):
                raise serializers.ValidationError(
                    "Online ISSN must be in format: 1234-5678"
                )
        return value
    
    def validate_editor_in_chief_email(self, value):
        """Validate that the editor-in-chief email exists."""
        if value:
            from apps.users.models import Profile
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                user = User.objects.get(email=value)
                if not hasattr(user, 'profile'):
                    raise serializers.ValidationError("User does not have a profile.")
            except User.DoesNotExist:
                raise serializers.ValidationError("User with this email does not exist.")
        return value


class JournalListSerializer(serializers.ModelSerializer):
    """Lightweight Journal serializer for list views."""
    
    submission_count = serializers.SerializerMethodField()
    editor_in_chief = serializers.SerializerMethodField()
    staff_members = serializers.SerializerMethodField()
    
    class Meta:
        model = Journal
        fields = (
            'id', 'title', 'short_name', 'publisher',
            'is_active', 'is_accepting_submissions',
            'issn_print', 'issn_online',
            'website_url', 'contact_email',
            'description', 'settings',
            'submission_count', 'editor_in_chief', 'staff_members', 'created_at'
        )
    
    def get_submission_count(self, obj):
        """Get total submission count."""
        return obj.submissions.count()
    
    def get_editor_in_chief(self, obj):
        """Get editor-in-chief info."""
        editor = obj.staff_members.filter(
            role='EDITOR_IN_CHIEF',
            is_active=True
        ).first()
        if editor:
            return {
                'id': editor.profile.id,
                'name': editor.profile.display_name,
                'email': editor.profile.user.email
            }
        return None
    
    def get_staff_members(self, obj):
        """Get all active staff members."""
        staff = obj.staff_members.filter(is_active=True).select_related('profile', 'profile__user')
        return [{
            'id': member.id,
            'profile_id': member.profile.id,
            'name': member.profile.display_name,
            'email': member.profile.user.email,
            'role': member.role,
            'permissions': member.permissions
        } for member in staff]


class JournalSettingsSerializer(serializers.ModelSerializer):
    """Serializer for Journal settings configuration."""
    
    class Meta:
        model = Journal
        fields = ('id', 'settings')
        read_only_fields = ('id',)
    
    def validate_settings(self, value):
        """Validate journal settings structure."""
        required_keys = [
            'submission_guidelines',
            'review_process',
            'publication_frequency',
            'file_requirements'
        ]
        
        # Ensure required configuration keys exist
        for key in required_keys:
            if key not in value:
                value[key] = {}
        
        # Initialize new array fields if not present
        if 'coauthor_roles' not in value:
            value['coauthor_roles'] = []
        if 'author_guidelines' not in value:
            value['author_guidelines'] = []
        if 'submission_requirements' not in value:
            value['submission_requirements'] = []
        
        # Validate coauthor_roles is an array of strings
        if 'coauthor_roles' in value:
            if not isinstance(value['coauthor_roles'], list):
                raise serializers.ValidationError(
                    "coauthor_roles must be an array of strings"
                )
            for role in value['coauthor_roles']:
                if not isinstance(role, str):
                    raise serializers.ValidationError(
                        "All coauthor_roles must be strings"
                    )
        
        # Validate author_guidelines is an array of strings
        if 'author_guidelines' in value:
            if not isinstance(value['author_guidelines'], list):
                raise serializers.ValidationError(
                    "author_guidelines must be an array of strings"
                )
            for guideline in value['author_guidelines']:
                if not isinstance(guideline, str):
                    raise serializers.ValidationError(
                        "All author_guidelines must be strings"
                    )
        
        # Validate submission_requirements is an array of strings
        if 'submission_requirements' in value:
            if not isinstance(value['submission_requirements'], list):
                raise serializers.ValidationError(
                    "submission_requirements must be an array of strings"
                )
            for requirement in value['submission_requirements']:
                if not isinstance(requirement, str):
                    raise serializers.ValidationError(
                        "All submission_requirements must be strings"
                    )
        
        # Validate file requirements
        if 'file_requirements' in value:
            file_req = value['file_requirements']
            if 'max_file_size' in file_req:
                try:
                    max_size = int(file_req['max_file_size'])
                    if max_size > 100 * 1024 * 1024:  # 100MB limit
                        raise serializers.ValidationError(
                            "Maximum file size cannot exceed 100MB"
                        )
                except (ValueError, TypeError):
                    raise serializers.ValidationError(
                        "max_file_size must be a valid integer (bytes)"
                    )
        
        return value


class AddStaffMemberSerializer(serializers.Serializer):
    """Serializer for adding staff members to journals."""
    
    profile_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=JournalStaff.STAFF_ROLE_CHOICES)
    permissions = serializers.JSONField(required=False, default=dict)
    
    def validate_profile_id(self, value):
        """Validate that profile exists."""
        from apps.users.models import Profile
        try:
            return Profile.objects.get(id=value)
        except Profile.DoesNotExist:
            raise serializers.ValidationError("Profile does not exist.")
    
    def validate(self, attrs):
        """Validate that user isn't already staff with this role."""
        profile = attrs['profile_id']
        role = attrs['role']
        journal = self.context['journal']
        
        existing = JournalStaff.objects.filter(
            journal=journal,
            profile=profile,
            role=role,
            is_active=True
        ).exists()
        
        if existing:
            raise serializers.ValidationError(
                f"User is already {role} for this journal."
            )
        
        return attrs


class SectionSerializer(serializers.ModelSerializer):
    """Serializer for journal Sections."""
    
    section_editor_name = serializers.CharField(
        source='section_editor.display_name',
        read_only=True,
        allow_null=True
    )
    category_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Section
        fields = (
            'id', 'journal', 'name', 'code', 'description',
            'section_editor', 'section_editor_name', 'order',
            'is_active', 'category_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_category_count(self, obj):
        """Get number of categories in this section."""
        return obj.categories.filter(is_active=True).count()
    
    def validate_code(self, value):
        """Validate code format."""
        import re
        if not re.match(r'^[A-Z0-9_]+$', value.upper()):
            raise serializers.ValidationError(
                "Code must contain only uppercase letters, numbers, and underscores."
            )
        return value.upper()


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Categories."""
    
    section_name = serializers.CharField(source='section.name', read_only=True)
    research_type_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = (
            'id', 'section', 'section_name', 'name', 'code',
            'description', 'order', 'is_active',
            'research_type_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_research_type_count(self, obj):
        """Get number of research types in this category."""
        return obj.research_types.filter(is_active=True).count()
    
    def validate_code(self, value):
        """Validate code format."""
        import re
        if not re.match(r'^[A-Z0-9_]+$', value.upper()):
            raise serializers.ValidationError(
                "Code must contain only uppercase letters, numbers, and underscores."
            )
        return value.upper()


class ResearchTypeSerializer(serializers.ModelSerializer):
    """Serializer for Research Types."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    area_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ResearchType
        fields = (
            'id', 'category', 'category_name', 'name', 'code',
            'description', 'requirements', 'order', 'is_active',
            'area_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_area_count(self, obj):
        """Get number of areas in this research type."""
        return obj.areas.filter(is_active=True).count()
    
    def validate_code(self, value):
        """Validate code format."""
        import re
        if not re.match(r'^[A-Z0-9_]+$', value.upper()):
            raise serializers.ValidationError(
                "Code must contain only uppercase letters, numbers, and underscores."
            )
        return value.upper()


class AreaSerializer(serializers.ModelSerializer):
    """Serializer for Areas."""
    
    research_type_name = serializers.CharField(source='research_type.name', read_only=True)
    
    class Meta:
        model = Area
        fields = (
            'id', 'research_type', 'research_type_name', 'name',
            'code', 'description', 'keywords', 'order', 'is_active',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def validate_code(self, value):
        """Validate code format."""
        import re
        if not re.match(r'^[A-Z0-9_]+$', value.upper()):
            raise serializers.ValidationError(
                "Code must contain only uppercase letters, numbers, and underscores."
            )
        return value.upper()
    
    def validate_keywords(self, value):
        """Validate keywords is a list of strings."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Keywords must be a list.")
        for keyword in value:
            if not isinstance(keyword, str):
                raise serializers.ValidationError("All keywords must be strings.")
        return value


class TaxonomyTreeSerializer(serializers.Serializer):
    """
    Serializer for complete taxonomy tree.
    Returns nested structure: Section -> Category -> ResearchType -> Area
    """
    id = serializers.UUIDField()
    name = serializers.CharField()
    code = serializers.CharField()
    categories = serializers.SerializerMethodField()
    
    def get_categories(self, section):
        """Get categories with nested research types and areas."""
        categories = section.categories.filter(is_active=True)
        result = []
        for category in categories:
            research_types = category.research_types.filter(is_active=True)
            rt_list = []
            for rt in research_types:
                areas = rt.areas.filter(is_active=True)
                rt_list.append({
                    'id': rt.id,
                    'name': rt.name,
                    'code': rt.code,
                    'areas': [
                        {
                            'id': area.id,
                            'name': area.name,
                            'code': area.code,
                            'keywords': area.keywords
                        }
                        for area in areas
                    ]
                })
            result.append({
                'id': category.id,
                'name': category.name,
                'code': category.code,
                'research_types': rt_list
            })
        return result