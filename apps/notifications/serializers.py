"""
Serializers for email notification preferences.
"""
from rest_framework import serializers
from apps.notifications.models import EmailNotificationPreference, EmailLog


class EmailNotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user email notification preferences."""
    
    class Meta:
        model = EmailNotificationPreference
        fields = [
            'id',
            'email_notifications_enabled',
            # Account notifications
            'email_on_login',
            'email_on_password_change',
            # ORCID notifications
            'email_on_orcid_connected',
            'email_on_orcid_disconnected',
            # Verification notifications
            'email_on_verification_submitted',
            'email_on_verification_approved',
            'email_on_verification_rejected',
            'email_on_verification_info_requested',
            # Submission notifications
            'email_on_submission_received',
            'email_on_submission_status_change',
            # Review notifications
            'email_on_review_assigned',
            'email_on_review_reminder',
            # Decision notifications
            'email_on_decision_made',
            # Digest options
            'enable_daily_digest',
            'enable_weekly_digest',
            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmailLogSerializer(serializers.ModelSerializer):
    """Serializer for email log records."""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    template_type_display = serializers.CharField(
        source='get_template_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = EmailLog
        fields = [
            'id',
            'recipient',
            'user_email',
            'template_type',
            'template_type_display',
            'subject',
            'status',
            'status_display',
            'sent_at',
            'retry_count',
            'error_message',
            'created_at',
        ]
        read_only_fields = fields
