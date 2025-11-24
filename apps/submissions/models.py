"""
Submission models for the Journal Portal.
Handles submissions, documents, versions, and authorship.
"""
import uuid
import hashlib
from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Submission(models.Model):
    """
    Main submission model representing manuscript submissions.
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('UNDER_REVIEW', 'Under Review'),
        ('REVISION_REQUESTED', 'Revision Requested'),  # Set by reviewer
        ('REVISION_REQUIRED', 'Revision Required'),    # Set by editor
        ('REVISED', 'Revised'),
        ('ACCEPTANCE_REQUESTED', 'Acceptance Requested'),  # Reviewer recommends accept
        ('REJECTION_REQUESTED', 'Rejection Requested'),    # Reviewer recommends reject
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('WITHDRAWN', 'Withdrawn'),
        ('PUBLISHED', 'Published'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Journal and basic info
    journal = models.ForeignKey(
        'journals.Journal',
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    title = models.CharField(max_length=500)
    abstract = models.TextField(help_text="Manuscript abstract")
    
    # Taxonomy classification
    section = models.ForeignKey(
        'journals.Section',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submissions',
        help_text="Journal section for this submission"
    )
    category = models.ForeignKey(
        'journals.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submissions',
        help_text="Category within the section"
    )
    research_type = models.ForeignKey(
        'journals.ResearchType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submissions',
        help_text="Type of research (Original, Review, etc.)"
    )
    area = models.ForeignKey(
        'journals.Area',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submissions',
        help_text="Specific research area"
    )
    
    # Authorship
    corresponding_author = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='corresponding_submissions'
    )
    coauthors = models.ManyToManyField(
        'users.Profile',
        through='AuthorContribution',
        related_name='coauthored_submissions',
        blank=True
    )
    
    # Submission status and workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    submission_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    
    # Review type configuration
    REVIEW_TYPE_CHOICES = [
        ('SINGLE_BLIND', 'Single Blind'),  # Reviewer knows author, author doesn't know reviewer
        ('DOUBLE_BLIND', 'Double Blind'),  # Both identities hidden
        ('OPEN', 'Open Review'),  # Both identities known
    ]
    review_type = models.CharField(
        max_length=20,
        choices=REVIEW_TYPE_CHOICES,
        default='SINGLE_BLIND',
        help_text="Type of peer review for this submission"
    )
    
    # Metadata and content
    metadata_json = models.JSONField(
        default=dict,
        help_text="Tags, keywords, funding info, ethics declarations, etc."
    )
    
    # Quality and compliance scores
    compliance_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Overall compliance score (0-100)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # OJS Integration
    ojs_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Open Journal Systems submission ID for this journal"
    )
    
    # Search vector for full-text search
    search_vector = SearchVectorField(null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['journal', 'status']),
            models.Index(fields=['corresponding_author']),
            models.Index(fields=['status', 'submitted_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['section', 'category']),
            models.Index(fields=['research_type', 'area']),
            GinIndex(fields=['search_vector']),
            GinIndex(fields=['metadata_json']),
        ]
        # CRITICAL: Prevent data collision between journals
        # Same OJS ID can exist in different journals
        unique_together = [['ojs_id', 'journal']]
    
    def __str__(self):
        return f"{self.title[:50]}... ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Generate submission number if not set and status is being changed to SUBMITTED or REVISED
        if not self.submission_number and self.status in ['SUBMITTED', 'REVISED']:
            from django.utils import timezone
            year = timezone.now().year
            count = Submission.objects.filter(
                journal=self.journal,
                created_at__year=year,
                submission_number__isnull=False
            ).exclude(pk=self.pk).count() + 1
            self.submission_number = f"{self.journal.short_name}-{year}-{count:04d}"
        
        super().save(*args, **kwargs)


class AuthorContribution(models.Model):
    """
    Through model for Submission-Profile relationship with contribution details.
    """
    CONTRIBUTION_ROLE_CHOICES = [
        ('CORRESPONDING', 'Corresponding Author'),
        ('FIRST', 'First Author'),
        ('CO_AUTHOR', 'Co-author'),
        ('SENIOR', 'Senior Author'),
        ('LAST', 'Last Author'),
    ]
    
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name='author_contributions'
    )
    profile = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='contributions'
    )
    
    # Author order and role
    order = models.PositiveIntegerField(help_text="Author order in the publication")
    contrib_role = models.CharField(max_length=20, choices=CONTRIBUTION_ROLE_CHOICES)
    
    # Contribution details
    contribution_details = models.JSONField(
        default=dict,
        help_text="Detailed contribution information (conceptualization, methodology, etc.)"
    )
    
    # Author agreement and verification
    has_agreed = models.BooleanField(default=False)
    agreed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['submission', 'profile']
        ordering = ['order']
        indexes = [
            models.Index(fields=['submission', 'order']),
        ]
    
    def __str__(self):
        return f"{self.profile} - {self.get_contrib_role_display()} (#{self.order})"


class Document(models.Model):
    """
    Document model for SuperDoc integration.
    SuperDoc handles version history, comments, and tracked changes via Yjs CRDT.
    We only store the binary Yjs state and original DOCX file.
    """
    DOCUMENT_TYPE_CHOICES = [
        ('MANUSCRIPT', 'Manuscript'),
        ('SUPPLEMENTARY', 'Supplementary Material'),
        ('COVER_LETTER', 'Cover Letter'),
        ('REVIEWER_RESPONSE', 'Response to Reviewers'),
        ('REVISED_MANUSCRIPT', 'Revised Manuscript'),
        ('FINAL_VERSION', 'Final Version'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    # Document metadata
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    description = models.TextField(blank=True)
    
    # Document management
    created_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='created_documents'
    )
    
    # SuperDoc Yjs state (binary CRDT data)
    # This stores ALL SuperDoc state: content, versions, comments, tracked changes
    yjs_state = models.BinaryField(
        null=True,
        blank=True,
        help_text="Binary Yjs state containing document content, versions, and comments"
    )
    
    # Original DOCX file
    original_file = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Original uploaded DOCX file"
    )
    file_name = models.CharField(max_length=255, blank=True, default='')
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    
    # Last edit tracking
    last_edited_at = models.DateTimeField(null=True, blank=True)
    last_edited_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='last_edited_documents'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['submission', 'document_type']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"


class DocumentVersion(models.Model):
    """
    Document version model for version control and history.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    
    # Version information
    version_number = models.PositiveIntegerField()
    change_summary = models.TextField(blank=True, help_text="Summary of changes in this version")
    
    # File information
    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    file_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of the file for integrity"
    )
    
    # Difference tracking
    diff_to_prev = models.JSONField(
        null=True,
        blank=True,
        help_text="Diff or patch information compared to previous version"
    )
    
    # Version management
    is_current = models.BooleanField(default=True)
    immutable_flag = models.BooleanField(
        default=False,
        help_text="Mark version as immutable (cannot be changed)"
    )
    
    # Created by
    created_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='created_versions'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['document', 'version_number']
        ordering = ['-version_number']
        indexes = [
            models.Index(fields=['document', 'version_number']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['is_current']),
        ]
    
    def __str__(self):
        return f"{self.document.title} v{self.version_number}"
    
    def save(self, *args, **kwargs):
        # Generate file hash
        if self.file and not self.file_hash:
            self.file_hash = self._generate_file_hash()
        
        # Set version number
        if not self.version_number:
            last_version = DocumentVersion.objects.filter(
                document=self.document
            ).order_by('-version_number').first()
            self.version_number = (last_version.version_number + 1) if last_version else 1
        
        super().save(*args, **kwargs)
        
        # Update document's current version
        if self.is_current:
            DocumentVersion.objects.filter(
                document=self.document
            ).exclude(id=self.id).update(is_current=False)
            
            self.document.current_version = self
            self.document.save()
    
    def _generate_file_hash(self):
        """Generate SHA-256 hash of the file."""
        hash_sha256 = hashlib.sha256()
        for chunk in self.file.chunks():
            hash_sha256.update(chunk)
        return hash_sha256.hexdigest()


class Comment(models.Model):
    """
    Comments and suggestions on document versions.
    """
    COMMENT_TYPE_CHOICES = [
        ('COMMENT', 'Comment'),
        ('SUGGESTION', 'Suggestion'),
        ('CORRECTION', 'Correction'),
        ('QUESTION', 'Question'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Comment metadata
    author = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='comments'
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    
    # Comment content
    comment_type = models.CharField(max_length=20, choices=COMMENT_TYPE_CHOICES)
    text = models.TextField()
    
    # Location in document
    location = models.JSONField(
        help_text="Location information (page, line, character position, etc.)"
    )
    
    # Comment status
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_comments'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Threading for replies
    parent_comment = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['document_version', 'resolved']),
            models.Index(fields=['author']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_comment_type_display()} by {self.author} on {self.document_version}"
