"""
Copyediting workflow models for the Journal Portal.
Handles copyediting assignments, files, and discussions after editorial acceptance.
"""
import uuid
from django.db import models
from django.utils import timezone


class CopyeditingAssignment(models.Model):
    """
    Copyediting assignment model for managing copyeditor assignments.
    Created when a submission moves to COPYEDITING stage after ACCEPTED decision.
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
        related_name='copyediting_assignments'
    )
    copyeditor = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='copyediting_assignments',
        help_text="Copyeditor assigned to this submission"
    )
    assigned_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='assigned_copyediting_tasks',
        help_text="Editor who assigned the copyeditor"
    )
    
    # Additional participants (optional collaborators)
    participants = models.ManyToManyField(
        'users.Profile',
        related_name='participating_copyediting_assignments',
        blank=True,
        help_text="Additional users who can collaborate on this assignment"
    )
    
    # Assignment status and dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(help_text="Deadline for copyediting completion")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Assignment instructions
    instructions = models.TextField(
        blank=True,
        help_text="Special instructions from editor to copyeditor"
    )
    
    # Completion notes
    completion_notes = models.TextField(
        blank=True,
        help_text="Notes from copyeditor upon completion"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['submission', 'status']),
            models.Index(fields=['copyeditor', 'status']),
            models.Index(fields=['status', 'due_date']),
        ]
    
    def __str__(self):
        return f"Copyediting: {self.submission.title[:30]}... by {self.copyeditor}"
    
    def save(self, *args, **kwargs):
        # Track status changes
        is_new = self._state.adding
        old_status = None
        if not is_new:
            try:
                old_instance = CopyeditingAssignment.objects.get(pk=self.pk)
                old_status = old_instance.status
            except CopyeditingAssignment.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Update timestamps based on status changes
        if old_status != self.status:
            if self.status == 'IN_PROGRESS' and not self.started_at:
                self.started_at = timezone.now()
                CopyeditingAssignment.objects.filter(pk=self.pk).update(started_at=self.started_at)
            elif self.status == 'COMPLETED' and not self.completed_at:
                self.completed_at = timezone.now()
                CopyeditingAssignment.objects.filter(pk=self.pk).update(completed_at=self.completed_at)


class CopyeditingFile(models.Model):
    """
    Files in copyediting workflow (both draft and copyedited versions).
    """
    FILE_TYPE_CHOICES = [
        ('DRAFT', 'Draft File'),  # Original file from submission
        ('COPYEDITED', 'Copyedited File'),  # File after copyediting
        ('FINAL', 'Final Approved'),  # Author-approved final version
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # File relationships
    assignment = models.ForeignKey(
        CopyeditingAssignment,
        on_delete=models.CASCADE,
        related_name='files'
    )
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='copyediting_files'
    )
    
    # File details
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file = models.FileField(
        upload_to='copyediting/%Y/%m/%d/',
        help_text="Copyediting file (draft or edited version)"
    )
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=100)
    
    # File metadata
    version = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='uploaded_copyediting_files'
    )
    
    # Approval tracking
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_copyediting_files'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Edit tracking (for manual save workflow like SuperDoc)
    last_edited_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='last_edited_copyediting_files',
        help_text="Last person to edit this file"
    )
    last_edited_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['assignment', 'file_type']),
            models.Index(fields=['submission', 'file_type']),
            models.Index(fields=['uploaded_by']),
        ]
    
    def __str__(self):
        return f"{self.get_file_type_display()}: {self.original_filename}"


class CopyeditingDiscussion(models.Model):
    """
    Discussion threads between copyeditor, author, and editor during copyediting.
    """
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Discussion details
    assignment = models.ForeignKey(
        CopyeditingAssignment,
        on_delete=models.CASCADE,
        related_name='discussions'
    )
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='copyediting_discussions'
    )
    
    # Discussion content
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    
    # Participants
    started_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='started_copyediting_discussions'
    )
    participants = models.ManyToManyField(
        'users.Profile',
        related_name='copyediting_discussions',
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
        related_name='closed_copyediting_discussions'
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


class CopyeditingMessage(models.Model):
    """
    Individual messages within a copyediting discussion thread.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Message relationships
    discussion = models.ForeignKey(
        CopyeditingDiscussion,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    # Message content
    author = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='copyediting_messages'
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


class CopyeditingMessageAttachment(models.Model):
    """
    File attachments for copyediting discussion messages.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Attachment relationships
    message = models.ForeignKey(
        CopyeditingMessage,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    
    # File details
    file = models.FileField(
        upload_to='copyediting/discussions/%Y/%m/%d/',
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
