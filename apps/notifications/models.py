"""
Email notification models for the Journal Portal.
Manages email templates and user notification preferences.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


class EmailTemplate(models.Model):
    """
    Email template model for customizable email notifications.
    """
    TEMPLATE_TYPES = [
        ('WELCOME', 'Welcome Email'),
        ('EMAIL_VERIFICATION', 'Email Verification'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('ORCID_CONNECTED', 'ORCID Connected'),
        ('ORCID_DISCONNECTED', 'ORCID Disconnected'),
        ('VERIFICATION_SUBMITTED', 'Verification Request Submitted'),
        ('VERIFICATION_APPROVED', 'Verification Request Approved'),
        ('VERIFICATION_REJECTED', 'Verification Request Rejected'),
        ('VERIFICATION_INFO_REQUESTED', 'Additional Information Requested'),
        ('VERIFICATION_USER_RESPONDED', 'User Responded to Info Request'),
        ('SUBMISSION_RECEIVED', 'Submission Received'),
        ('REVIEW_ASSIGNED', 'Review Assigned'),
        ('REVIEW_COMPLETED', 'Review Completed'),
        ('DECISION_MADE', 'Editorial Decision'),
        # Phase 4: Review System Templates
        ('REVIEW_INVITATION', 'Review Invitation'),
        ('REVIEW_REMINDER', 'Review Deadline Reminder'),
        ('REVIEW_SUBMITTED', 'Review Submitted Confirmation'),
        ('EDITORIAL_DECISION_ACCEPT', 'Manuscript Accepted'),
        ('EDITORIAL_DECISION_REJECT', 'Manuscript Rejected'),
        ('REVISION_REQUESTED', 'Revisions Requested'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template identification
    template_type = models.CharField(
        max_length=50,
        choices=TEMPLATE_TYPES,
        unique=True,
        help_text="Type of email template"
    )
    name = models.CharField(
        max_length=200,
        help_text="Human-readable template name"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of when this template is used"
    )
    
    # Email content
    subject = models.CharField(
        max_length=255,
        help_text="Email subject line (supports variables)"
    )
    html_body = models.TextField(
        help_text="HTML email body (supports variables)"
    )
    text_body = models.TextField(
        blank=True,
        help_text="Plain text fallback (auto-generated if empty)"
    )
    
    # Template variables
    available_variables = models.JSONField(
        default=list,
        help_text="List of available template variables"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is currently in use"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['template_type']
        indexes = [
            models.Index(fields=['template_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class EmailNotificationPreference(models.Model):
    """
    User email notification preferences.
    Controls which emails users want to receive.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='email_preferences',
        help_text="User these preferences belong to"
    )
    
    # Account notifications
    email_on_login = models.BooleanField(
        default=False,
        help_text="Notify on new login"
    )
    email_on_password_change = models.BooleanField(
        default=True,
        help_text="Notify on password change"
    )
    
    # ORCID notifications
    email_on_orcid_connected = models.BooleanField(
        default=True,
        help_text="Notify when ORCID is connected"
    )
    email_on_orcid_disconnected = models.BooleanField(
        default=True,
        help_text="Notify when ORCID is disconnected"
    )
    
    # Verification notifications
    email_on_verification_submitted = models.BooleanField(
        default=True,
        help_text="Notify when verification request is submitted"
    )
    email_on_verification_approved = models.BooleanField(
        default=True,
        help_text="Notify when verification is approved"
    )
    email_on_verification_rejected = models.BooleanField(
        default=True,
        help_text="Notify when verification is rejected"
    )
    email_on_verification_info_requested = models.BooleanField(
        default=True,
        help_text="Notify when admin requests additional information"
    )
    
    # Submission notifications
    email_on_submission_received = models.BooleanField(
        default=True,
        help_text="Notify when submission is received"
    )
    email_on_submission_status_change = models.BooleanField(
        default=True,
        help_text="Notify on submission status changes"
    )
    
    # Review notifications
    email_on_review_assigned = models.BooleanField(
        default=True,
        help_text="Notify when review is assigned"
    )
    email_on_review_reminder = models.BooleanField(
        default=True,
        help_text="Send review deadline reminders"
    )
    
    # Decision notifications
    email_on_decision_made = models.BooleanField(
        default=True,
        help_text="Notify when editorial decision is made"
    )
    
    # Digest options
    enable_daily_digest = models.BooleanField(
        default=False,
        help_text="Receive daily digest of activities"
    )
    enable_weekly_digest = models.BooleanField(
        default=False,
        help_text="Receive weekly digest of activities"
    )
    
    # Global control
    email_notifications_enabled = models.BooleanField(
        default=True,
        help_text="Master switch for all email notifications"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Email Notification Preference"
        verbose_name_plural = "Email Notification Preferences"
    
    def __str__(self):
        return f"Email preferences for {self.user.email}"


class EmailLog(models.Model):
    """
    Log of all emails sent by the system.
    Tracks delivery status and errors.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('BOUNCED', 'Bounced'),
        ('DELIVERED', 'Delivered'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Email details
    recipient = models.EmailField(help_text="Recipient email address")
    user = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sent_emails',
        help_text="User this email was sent to"
    )
    
    template_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type of email template used"
    )
    
    subject = models.CharField(max_length=255)
    body_html = models.TextField(blank=True)
    body_text = models.TextField(blank=True)
    
    # Delivery tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    # Metadata
    context_data = models.JSONField(
        default=dict,
        help_text="Template context data used"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['user', 'template_type']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Email to {self.recipient} - {self.status}"
