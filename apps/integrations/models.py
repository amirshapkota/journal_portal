"""
Integration models for the Journal Portal.
Handles external service integrations and mappings.
"""
import uuid
from django.db import models
from django.core.validators import URLValidator


class OJSMapping(models.Model):
    """
    Mapping model for OJS (Open Journal Systems) integration.
    Tracks synchronization between local submissions and OJS.
    Now uses Journal's OJS connection details instead of global settings.
    """
    SYNC_DIRECTION_CHOICES = [
        ('TO_OJS', 'To OJS'),
        ('FROM_OJS', 'From OJS'),
        ('BIDIRECTIONAL', 'Bidirectional'),
    ]
    
    SYNC_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CONFLICT', 'Conflict'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Local submission reference
    local_submission = models.OneToOneField(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='ojs_mapping'
    )
    
    # OJS reference (now derived from journal's OJS settings)
    ojs_submission_id = models.CharField(
        max_length=100,
        help_text="OJS submission ID"
    )
    
    # Synchronization details
    sync_direction = models.CharField(
        max_length=20,
        choices=SYNC_DIRECTION_CHOICES,
        default='TO_OJS'
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default='PENDING'
    )
    
    # Synchronization metadata
    sync_metadata = models.JSONField(
        default=dict,
        help_text="Metadata about synchronization process and conflicts"
    )
    error_log = models.TextField(blank=True)
    
    # Version tracking
    local_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Local version identifier for conflict resolution"
    )
    ojs_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="OJS version identifier for conflict resolution"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['ojs_submission_id']),
            models.Index(fields=['sync_status', 'last_synced_at']),
            models.Index(fields=['local_submission']),
        ]
    
    def __str__(self):
        return f"OJS mapping: {self.local_submission.title[:30]}... <-> {self.ojs_submission_id}"
    
    @property
    def journal(self):
        """Get the journal from the submission."""
        return self.local_submission.journal
    
    def get_ojs_credentials(self):
        """Get OJS API credentials from the journal."""
        journal = self.journal
        if not journal.ojs_enabled:
            return None
        return {
            'api_url': journal.ojs_api_url,
            'api_key': journal.ojs_api_key,
            'journal_id': journal.ojs_journal_id
        }


class ORCIDIntegration(models.Model):
    """
    ORCID integration tracking for user profiles.
    """
    SYNC_STATUS_CHOICES = [
        ('CONNECTED', 'Connected'),
        ('DISCONNECTED', 'Disconnected'),
        ('ERROR', 'Error'),
        ('TOKEN_EXPIRED', 'Token Expired'),
        ('PENDING_VERIFICATION', 'Pending Verification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Profile reference
    profile = models.OneToOneField(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='orcid_integration'
    )
    
    # ORCID details
    orcid_id = models.CharField(
        max_length=19,
        help_text="ORCID identifier (e.g., 0000-0000-0000-0000)"
    )
    access_token_encrypted = models.BinaryField(
        help_text="Encrypted ORCID access token"
    )
    refresh_token_encrypted = models.BinaryField(
        null=True,
        blank=True,
        help_text="Encrypted ORCID refresh token"
    )
    
    # Token metadata
    token_scope = models.CharField(
        max_length=255,
        blank=True,
        help_text="ORCID token scope/permissions"
    )
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Synchronization details
    status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default='PENDING_VERIFICATION'
    )
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_errors = models.TextField(blank=True)
    
    # ORCID data cache
    orcid_data = models.JSONField(
        default=dict,
        help_text="Cached ORCID profile data"
    )
    works_data = models.JSONField(
        default=list,
        help_text="Cached ORCID works data"
    )
    
    # Sync preferences
    auto_sync_enabled = models.BooleanField(default=True)
    sync_publications = models.BooleanField(default=True)
    sync_employment = models.BooleanField(default=True)
    sync_education = models.BooleanField(default=True)
    
    # Timestamps
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['orcid_id']),
            models.Index(fields=['status']),
            models.Index(fields=['last_sync_at']),
        ]
    
    def __str__(self):
        return f"ORCID integration for {self.profile} ({self.orcid_id})"


class ORCIDOAuthState(models.Model):
    """
    Temporary storage for ORCID OAuth state tokens.
    Allows OAuth flow to work across different sessions (API -> Browser redirect).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # State token for OAuth security
    state_token = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique state token for OAuth flow"
    )
    
    # User reference
    user = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.CASCADE,
        related_name='orcid_oauth_states'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="State token expiration time (usually 10 minutes)"
    )
    used = models.BooleanField(
        default=False,
        help_text="Whether this state token has been used"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['state_token', 'used']),
            models.Index(fields=['expires_at', 'used']),
        ]
    
    def __str__(self):
        return f"OAuth state for {self.user.email} - {self.state_token[:10]}..."


class ExternalServiceIntegration(models.Model):
    """
    Generic external service integration model.
    """
    SERVICE_TYPE_CHOICES = [
        ('ITHENTICATE', 'iThenticate'),
        ('TURNITIN', 'Turnitin'),
        ('CROSSREF', 'Crossref'),
        ('ROR', 'Research Organization Registry'),
        ('OPENALEX', 'OpenAlex'),
        ('PUBMED', 'PubMed'),
        ('SCOPUS', 'Scopus'),
        ('WOS', 'Web of Science'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('ERROR', 'Error'),
        ('RATE_LIMITED', 'Rate Limited'),
        ('MAINTENANCE', 'Maintenance'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Service details
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES)
    service_name = models.CharField(max_length=100)
    service_url = models.URLField(validators=[URLValidator()])
    
    # API configuration
    api_endpoint = models.URLField(blank=True)
    api_key_encrypted = models.BinaryField(
        null=True,
        blank=True,
        help_text="Encrypted API key"
    )
    api_version = models.CharField(max_length=20, blank=True)
    
    # Service status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    last_checked_at = models.DateTimeField(null=True, blank=True)
    response_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Last response time in milliseconds"
    )
    
    # Usage tracking
    total_requests = models.PositiveIntegerField(default=0)
    successful_requests = models.PositiveIntegerField(default=0)
    failed_requests = models.PositiveIntegerField(default=0)
    
    # Rate limiting
    rate_limit_requests = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Requests allowed per rate limit period"
    )
    rate_limit_period_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Rate limit period in seconds"
    )
    
    # Configuration
    configuration = models.JSONField(
        default=dict,
        help_text="Service-specific configuration"
    )
    
    # Error tracking
    last_error = models.TextField(blank=True)
    error_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['service_type', 'service_name']
        indexes = [
            models.Index(fields=['service_type', 'status']),
            models.Index(fields=['status', 'last_checked_at']),
        ]
    
    def __str__(self):
        return f"{self.service_name} ({self.get_service_type_display()})"
    
    def get_success_rate(self):
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0
        return (self.successful_requests / self.total_requests) * 100


class SyncLog(models.Model):
    """
    Log of synchronization activities with external services.
    """
    SYNC_TYPE_CHOICES = [
        ('OJS_SUBMISSION', 'OJS Submission'),
        ('ORCID_PROFILE', 'ORCID Profile'),
        ('ORCID_WORKS', 'ORCID Works'),
        ('PLAGIARISM_CHECK', 'Plagiarism Check'),
        ('REFERENCE_CHECK', 'Reference Check'),
        ('METADATA_ENRICHMENT', 'Metadata Enrichment'),
    ]
    
    STATUS_CHOICES = [
        ('STARTED', 'Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Sync details
    sync_type = models.CharField(max_length=30, choices=SYNC_TYPE_CHOICES)
    external_service = models.ForeignKey(
        ExternalServiceIntegration,
        on_delete=models.CASCADE,
        related_name='sync_logs'
    )
    
    # Resource references
    resource_type = models.CharField(max_length=30)
    resource_id = models.CharField(max_length=100)
    
    # Sync execution
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='STARTED')
    started_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_syncs'
    )
    
    # Sync results
    records_processed = models.PositiveIntegerField(default=0)
    records_updated = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    records_failed = models.PositiveIntegerField(default=0)
    
    # Sync metadata
    sync_metadata = models.JSONField(
        default=dict,
        help_text="Sync execution metadata and results"
    )
    error_details = models.TextField(blank=True)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['sync_type', 'status']),
            models.Index(fields=['external_service', 'started_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['status', 'started_at']),
        ]
    
    def __str__(self):
        return f"{self.get_sync_type_display()} with {self.external_service.service_name} - {self.get_status_display()}"
