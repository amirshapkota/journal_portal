"""
Journal models for the Journal Portal.
Handles journal management and configuration.
"""
import uuid
from django.db import models
from django.conf import settings


class Journal(models.Model):
    """
    Journal model representing academic journals in the system.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic journal information
    title = models.CharField(max_length=255, help_text="Full journal title")
    short_name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Short name or abbreviation for the journal"
    )
    publisher = models.CharField(max_length=255, blank=True)
    
    # Journal description and metadata
    description = models.TextField(blank=True)
    issn_print = models.CharField(max_length=9, blank=True, help_text="Print ISSN (e.g., 1234-5678)")
    issn_online = models.CharField(max_length=9, blank=True, help_text="Online ISSN (e.g., 1234-5679)")
    
    # Journal website and contact
    website_url = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    
    # OJS Integration Settings
    ojs_enabled = models.BooleanField(
        default=False,
        help_text="Enable OJS sync for this journal"
    )
    ojs_api_url = models.URLField(
        blank=True,
        help_text="OJS API base URL for this journal (e.g., https://journal.com/index.php/journal/api/v1)"
    )
    ojs_api_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="API key for OJS authentication"
    )
    ojs_journal_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Journal ID in OJS system"
    )
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful sync with OJS"
    )
    sync_enabled = models.BooleanField(
        default=True,
        help_text="Enable automatic background sync for this journal"
    )
    sync_interval_hours = models.IntegerField(
        default=1,
        help_text="Sync interval in hours (default: 1 hour)"
    )
    
    # Journal settings and configuration
    settings = models.JSONField(
        default=dict,
        help_text="Journal-specific settings and configuration"
    )
    
    # Editorial team
    editor_group = models.ManyToManyField(
        'users.Profile',
        through='JournalStaff',
        related_name='managed_journals',
        blank=True
    )
    
    # Journal status
    is_active = models.BooleanField(default=True)
    is_accepting_submissions = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['short_name']),
            models.Index(fields=['is_active', 'is_accepting_submissions']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_short_name(self):
        """Return short name for display purposes."""
        return self.short_name or self.title[:20]


class JournalStaff(models.Model):
    """
    Through model for Journal-Profile relationship with roles.
    """
    STAFF_ROLE_CHOICES = [
        ('EDITOR_IN_CHIEF', 'Editor-in-Chief'),
        ('MANAGING_EDITOR', 'Managing Editor'),
        ('ASSOCIATE_EDITOR', 'Associate Editor'),
        ('GUEST_EDITOR', 'Guest Editor'),
        ('SECTION_EDITOR', 'Section Editor'),
        ('COPY_EDITOR', 'Copy Editor'),
        ('LAYOUT_EDITOR', 'Layout Editor'),
        ('PROOFREADER', 'Proofreader'),
    ]
    
    journal = models.ForeignKey(
        Journal,
        on_delete=models.CASCADE,
        related_name='staff_members'
    )
    profile = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='journal_positions'
    )
    role = models.CharField(max_length=50, choices=STAFF_ROLE_CHOICES)
    
    # Role details
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Permissions and responsibilities
    permissions = models.JSONField(
        default=dict,
        help_text="Staff member specific permissions"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['journal', 'profile', 'role']
        indexes = [
            models.Index(fields=['journal', 'is_active']),
            models.Index(fields=['profile', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.profile} - {self.get_role_display()} at {self.journal.short_name}"
