"""
Serializers for common app models.
"""
from rest_framework import serializers
from .models import ActivityLog, VerificationTicket, Concept, Embedding, AnomalyEvent, Award


class ActivityLogSerializer(serializers.ModelSerializer):
    """
    Serializer for ActivityLog model.
    Provides detailed information about system events for admin monitoring.
    """
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True, allow_null=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    actor_type_display = serializers.CharField(source='get_actor_type_display', read_only=True)
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id',
            'user_id',
            'user_email',
            'actor_type',
            'actor_type_display',
            'action_type',
            'action_type_display',
            'resource_type',
            'resource_type_display',
            'resource_id',
            'metadata',
            'ip_address',
            'user_agent',
            'session_id',
            'created_at',
        ]
        read_only_fields = fields


class VerificationTicketSerializer(serializers.ModelSerializer):
    """
    Serializer for VerificationTicket model.
    """
    profile_name = serializers.CharField(source='profile.get_full_name', read_only=True)
    requested_role_display = serializers.CharField(source='get_requested_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = VerificationTicket
        fields = [
            'id',
            'profile',
            'profile_name',
            'requested_role',
            'requested_role_display',
            'status',
            'status_display',
            'evidence',
            'ml_score',
            'ml_reasoning',
            'reviewed_by',
            'reviewed_at',
            'review_notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'ml_score', 'ml_reasoning']


class ConceptSerializer(serializers.ModelSerializer):
    """
    Serializer for Concept model.
    """
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    
    class Meta:
        model = Concept
        fields = [
            'id',
            'name',
            'description',
            'provider',
            'provider_display',
            'external_id',
            'parent_concept',
            'metadata',
            'usage_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'usage_count']


class AnomalyEventSerializer(serializers.ModelSerializer):
    """
    Serializer for AnomalyEvent model.
    """
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    handled_by_name = serializers.CharField(source='handled_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = AnomalyEvent
        fields = [
            'id',
            'event_type',
            'event_type_display',
            'severity',
            'severity_display',
            'resource_type',
            'resource_id',
            'anomaly_score',
            'evidence',
            'detector_name',
            'detector_version',
            'detection_confidence',
            'is_handled',
            'handled_by',
            'handled_by_name',
            'handled_at',
            'resolution_notes',
            'is_false_positive',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AwardSerializer(serializers.ModelSerializer):
    """
    Serializer for Award model.
    """
    profile_name = serializers.CharField(source='profile.get_full_name', read_only=True)
    badge_type_display = serializers.CharField(source='get_badge_type_display', read_only=True)
    awarded_by_name = serializers.CharField(source='awarded_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Award
        fields = [
            'id',
            'profile',
            'profile_name',
            'badge_type',
            'badge_type_display',
            'title',
            'description',
            'criteria_met',
            'evidence',
            'points_value',
            'is_public',
            'awarded_by',
            'awarded_by_name',
            'auto_awarded',
            'awarded_at',
        ]
        read_only_fields = ['id', 'awarded_at']
