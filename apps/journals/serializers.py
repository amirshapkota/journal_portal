"""
Serializers for Journal management.
Handles journal CRUD, staff management, and configuration.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Journal, JournalStaff
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
    
    class Meta:
        model = Journal
        fields = (
            'id', 'title', 'short_name', 'publisher', 'description',
            'issn_print', 'issn_online', 'website_url', 'contact_email',
            'settings', 'is_active', 'is_accepting_submissions',
            'staff_members', 'submission_count', 'active_staff_count',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_submission_count(self, obj):
        """Get total submission count for this journal."""
        return obj.submissions.count()
    
    def get_active_staff_count(self, obj):
        """Get active staff member count."""
        return obj.staff_members.filter(is_active=True).count()
    
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
            if not re.match(r'^\d{4}-\d{4}$', value):
                raise serializers.ValidationError(
                    "ISSN must be in format: 1234-5678"
                )
        return value
    
    def validate_issn_online(self, value):
        """Validate online ISSN format."""
        if value:
            import re
            if not re.match(r'^\d{4}-\d{4}$', value):
                raise serializers.ValidationError(
                    "Online ISSN must be in format: 1234-5678"
                )
        return value


class JournalListSerializer(serializers.ModelSerializer):
    """Lightweight Journal serializer for list views."""
    
    submission_count = serializers.SerializerMethodField()
    editor_in_chief = serializers.SerializerMethodField()
    
    class Meta:
        model = Journal
        fields = (
            'id', 'title', 'short_name', 'publisher',
            'is_active', 'is_accepting_submissions',
            'submission_count', 'editor_in_chief', 'created_at'
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