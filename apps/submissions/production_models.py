"""
Production workflow models for the Journal Portal.
Handles production assignments, galley files, and discussions after copyediting completion.
"""
import uuid
from django.db import models
from django.utils import timezone


class ProductionAssignment(models.Model):
    """
    Production assignment model for managing production assistant assignments.
    Created when a submission moves to IN_PRODUCTION stage after copyediting.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Assignment details
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='production_assignments'
    )
    production_assistant = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='production_assignments',
        help_text="Production assistant or layout editor assigned"
    )
    assigned_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='assigned_production_tasks',
        help_text="Editor who assigned the production assistant"
    )
    
    # Assignment status and dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(help_text="Deadline for production completion")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Assignment instructions
    instructions = models.TextField(
        blank=True,
        help_text="Special instructions from editor to production assistant"
    )
    
    # Completion notes
    completion_notes = models.TextField(
        blank=True,
        help_text="Notes from production assistant upon completion"
    )
    
    # Participants
    participants = models.ManyToManyField(
        'users.Profile',
        related_name='production_participants',
        blank=True,
        help_text="Additional participants involved in this production assignment"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['submission', 'status']),
            models.Index(fields=['production_assistant', 'status']),
            models.Index(fields=['status', 'due_date']),
        ]
    
    def __str__(self):
        return f"Production: {self.submission.title[:30]}... by {self.production_assistant}"
    
    def save(self, *args, **kwargs):
        # Track status changes
        is_new = self._state.adding
        old_status = None
        if not is_new:
            try:
                old_instance = ProductionAssignment.objects.get(pk=self.pk)
                old_status = old_instance.status
            except ProductionAssignment.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Update timestamps based on status changes
        if old_status != self.status:
            if self.status == 'IN_PROGRESS' and not self.started_at:
                self.started_at = timezone.now()
                ProductionAssignment.objects.filter(pk=self.pk).update(started_at=self.started_at)
            elif self.status == 'COMPLETED' and not self.completed_at:
                self.completed_at = timezone.now()
                ProductionAssignment.objects.filter(pk=self.pk).update(completed_at=self.completed_at)


class ProductionFile(models.Model):
    """
    Galley files and production-ready files.
    Galleys are publication-ready files in various formats (PDF, HTML, XML, etc.)
    """
    FILE_TYPE_CHOICES = [
        ('PRODUCTION_READY', 'Production Ready'),  # Final copyedited file
        ('GALLEY', 'Galley File'),  # Publication-ready format
    ]
    
    GALLEY_FORMAT_CHOICES = [
        ('PDF', 'PDF'),
        ('HTML', 'HTML'),
        ('XML', 'XML'),
        ('EPUB', 'EPUB'),
        ('MOBI', 'MOBI'),
        ('OTHER', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # File relationships
    assignment = models.ForeignKey(
        ProductionAssignment,
        on_delete=models.CASCADE,
        related_name='files'
    )
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='production_files'
    )
    
    # File details
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    galley_format = models.CharField(
        max_length=20,
        choices=GALLEY_FORMAT_CHOICES,
        null=True,
        blank=True,
        help_text="Format for galley files"
    )
    file = models.FileField(
        upload_to='production/%Y/%m/%d/',
        help_text="Production file (ready file or galley)"
    )
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=100)
    
    # File metadata
    label = models.CharField(
        max_length=100,
        help_text="Display label for the galley (e.g., 'PDF', 'Full Text HTML')"
    )
    version = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='uploaded_production_files'
    )
    
    # Publication status
    is_published = models.BooleanField(
        default=False,
        help_text="Whether this galley is published and visible to readers"
    )
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Approval tracking
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_production_files'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['assignment', 'file_type']),
            models.Index(fields=['submission', 'file_type', 'is_published']),
            models.Index(fields=['uploaded_by']),
        ]
    
    def __str__(self):
        return f"{self.label}: {self.original_filename}"


class ProductionDiscussion(models.Model):
    """
    Discussion threads between production assistant, author, and editor during production.
    """
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Discussion details
    assignment = models.ForeignKey(
        ProductionAssignment,
        on_delete=models.CASCADE,
        related_name='discussions'
    )
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='production_discussions'
    )
    
    # Discussion content
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    
    # Participants
    started_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='started_production_discussions'
    )
    participants = models.ManyToManyField(
        'users.Profile',
        related_name='production_discussions',
        help_text="Users involved in this discussion"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_production_discussions'
    )
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['assignment', 'status']),
            models.Index(fields=['submission', 'status']),
            models.Index(fields=['started_by']),
        ]
    
    def __str__(self):
        return f"{self.subject} - {self.submission.title[:30]}..."


class ProductionMessage(models.Model):
    """
    Individual messages within a production discussion thread.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Message relationships
    discussion = models.ForeignKey(
        ProductionDiscussion,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    # Message content
    author = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='production_messages'
    )
    message = models.TextField(help_text="Message content (supports HTML)")
    
    # Attachments
    has_attachments = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['discussion', 'created_at']),
            models.Index(fields=['author']),
        ]
    
    def __str__(self):
        return f"Message by {self.author} in {self.discussion.subject}"


class ProductionMessageAttachment(models.Model):
    """
    File attachments for production discussion messages.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Attachment relationships
    message = models.ForeignKey(
        ProductionMessage,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    
    # File details
    file = models.FileField(
        upload_to='production/discussions/%Y/%m/%d/',
        help_text="Discussion attachment file"
    )
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=100)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Attachment: {self.original_filename}"


class PublicationSchedule(models.Model):
    """
    Publication schedule for submissions ready to be published.
    """
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('PUBLISHED', 'Published'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Publication details
    submission = models.OneToOneField(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='publication_schedule'
    )
    
    # Schedule information
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    scheduled_date = models.DateTimeField(
        help_text="Date and time when article should be published"
    )
    published_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual publication date"
    )
    
    # Publication metadata
    volume = models.CharField(max_length=50, blank=True)
    issue = models.CharField(max_length=50, blank=True)
    year = models.PositiveIntegerField()
    doi = models.CharField(
        max_length=255,
        blank=True,
        help_text="Digital Object Identifier"
    )
    pages = models.CharField(
        max_length=50,
        blank=True,
        help_text="Page range (e.g., '123-145')"
    )
    
    # Scheduling metadata
    scheduled_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='scheduled_publications'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_date']
        indexes = [
            models.Index(fields=['submission', 'status']),
            models.Index(fields=['status', 'scheduled_date']),
            models.Index(fields=['scheduled_by']),
        ]
    
    def __str__(self):
        return f"Publication: {self.submission.title[:30]}... ({self.get_status_display()})"
