"""
Serializers for verification system.
"""
from rest_framework import serializers
from apps.users.models import VerificationRequest, Profile


class VerificationRequestSerializer(serializers.ModelSerializer):
    """Basic serializer for verification requests."""
    profile_email = serializers.EmailField(source='profile.user.email', read_only=True)
    profile_name = serializers.CharField(source='profile.display_name', read_only=True)
    
    class Meta:
        model = VerificationRequest
        fields = [
            'id', 'profile_email', 'profile_name', 'requested_roles', 'status',
            'affiliation', 'affiliation_email', 'orcid_verified', 'orcid_id',
            'auto_score', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'orcid_verified', 'orcid_id', 'auto_score', 'created_at', 'updated_at']


class VerificationRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating verification requests."""
    
    class Meta:
        model = VerificationRequest
        fields = [
            'id', 'requested_roles', 'affiliation', 'affiliation_email',
            'research_interests', 'academic_position', 'supporting_letter',
            'auto_score', 'orcid_verified', 'orcid_id', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'auto_score', 'orcid_verified', 'orcid_id', 'status', 'created_at']
    
    def validate_requested_roles(self, value):
        """Validate requested roles array."""
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one role must be requested.")
        
        valid_roles = ['AUTHOR', 'REVIEWER']
        for role in value:
            if role not in valid_roles:
                raise serializers.ValidationError(f"Invalid role: {role}. Must be one of {valid_roles}")
        
        # Remove duplicates
        return list(set(value))
    
    def validate(self, data):
        """Validate verification request data."""
        # Check if user already has a pending request
        profile = self.context['request'].user.profile
        pending_requests = VerificationRequest.objects.filter(
            profile=profile,
            status__in=['PENDING', 'INFO_REQUESTED']
        )
        
        if pending_requests.exists():
            raise serializers.ValidationError(
                "You already have a pending verification request. "
                "Please wait for it to be reviewed before submitting another."
            )
        
        return data


class VerificationRequestDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for verification requests."""
    profile_email = serializers.EmailField(source='profile.user.email', read_only=True)
    profile_name = serializers.CharField(source='profile.display_name', read_only=True)
    profile_id = serializers.UUIDField(source='profile.id', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = VerificationRequest
        fields = [
            'id', 'profile_id', 'profile_email', 'profile_name',
            'requested_roles', 'status', 'affiliation', 'affiliation_email',
            'research_interests', 'academic_position', 'supporting_letter',
            'orcid_verified', 'orcid_id', 'auto_score', 'score_details',
            'reviewed_by_email', 'reviewed_at', 'admin_notes',
            'rejection_reason', 'additional_info_requested',
            'user_response', 'user_response_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'profile_id', 'profile_email', 'profile_name',
            'status', 'orcid_verified', 'orcid_id', 'auto_score', 'score_details',
            'reviewed_by_email', 'reviewed_at', 'admin_notes',
            'rejection_reason', 'additional_info_requested',
            'created_at', 'updated_at'
        ]


class VerificationReviewSerializer(serializers.Serializer):
    """Serializer for admin review actions."""
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    additional_info_requested = serializers.CharField(required=False, allow_blank=True)


class VerificationResponseSerializer(serializers.Serializer):
    """Serializer for user response to info request."""
    response = serializers.CharField(required=True, min_length=10)
