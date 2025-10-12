"""
Precheck models for the Journal Portal.
Handles plagiarism detection, formatting validation, and pre-submission checks.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class PlagiarismReport(models.Model):
    """
    Plagiarism report model for tracking plagiarism checks.
    """
    PROVIDER_CHOICES = [
        ('ITHENTICATE', 'iThenticate'),
        ('TURNITIN', 'Turnitin'),
        ('CROSSREF', 'Crossref Similarity Check'),
        ('INTERNAL', 'Internal System'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('EXPIRED', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Report target
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='plagiarism_reports'
    )
    document_version = models.ForeignKey(
        'submissions.DocumentVersion',
        on_delete=models.CASCADE,
        related_name='plagiarism_reports'
    )
    
    # Provider information
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_report_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="External provider's report ID"
    )
    
    # Report details
    report_url = models.URLField(
        blank=True,
        help_text="URL to the detailed plagiarism report"
    )
    similarity_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Overall similarity percentage (0-100)"
    )
    
    # Matched items and details
    matched_items = models.JSONField(
        default=list,
        help_text="List of matched sources and similarity details"
    )
    
    # Report metadata
    report_metadata = models.JSONField(
        default=dict,
        help_text="Additional report metadata and configuration"
    )
    
    # Status and processing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(blank=True)
    
    # Report lifecycle
    requested_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='requested_plagiarism_reports'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['submission', 'status']),
            models.Index(fields=['document_version']),
            models.Index(fields=['provider', 'provider_report_id']),
            models.Index(fields=['similarity_score']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Plagiarism report for {self.submission.title[:30]}... ({self.similarity_score}%)"
    
    def is_high_similarity(self):
        """Check if similarity score exceeds threshold."""
        from django.conf import settings
        threshold = getattr(settings, 'JOURNAL_PORTAL', {}).get('PLAGIARISM_THRESHOLD', 15)
        return self.similarity_score > threshold
    
    def get_major_matches(self, threshold=5.0):
        """Get matches above a certain threshold."""
        return [
            match for match in self.matched_items
            if match.get('similarity_percentage', 0) > threshold
        ]


class FormatCheck(models.Model):
    """
    Format validation check for document formatting and compliance.
    """
    CHECK_TYPE_CHOICES = [
        ('MANUSCRIPT_FORMAT', 'Manuscript Format'),
        ('REFERENCE_FORMAT', 'Reference Format'),
        ('FIGURE_QUALITY', 'Figure Quality'),
        ('TABLE_FORMAT', 'Table Format'),
        ('METADATA_COMPLETENESS', 'Metadata Completeness'),
        ('FILE_COMPLIANCE', 'File Compliance'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Check target
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='format_checks'
    )
    document_version = models.ForeignKey(
        'submissions.DocumentVersion',
        on_delete=models.CASCADE,
        related_name='format_checks'
    )
    
    # Check details
    check_type = models.CharField(max_length=30, choices=CHECK_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Check results
    is_compliant = models.BooleanField(null=True, blank=True)
    compliance_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Compliance score (0-100)"
    )
    
    # Issues and recommendations
    issues_found = models.JSONField(
        default=list,
        help_text="List of formatting issues found"
    )
    recommendations = models.JSONField(
        default=list,
        help_text="Formatting recommendations"
    )
    
    # Processing details
    checker_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Version of the format checker used"
    )
    error_message = models.TextField(blank=True)
    
    # Check lifecycle
    requested_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='requested_format_checks'
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['submission', 'check_type']),
            models.Index(fields=['document_version', 'check_type']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['is_compliant']),
        ]
    
    def __str__(self):
        return f"{self.get_check_type_display()} check for {self.submission.title[:30]}..."


class RequirementCheck(models.Model):
    """
    Check for required documents and information completeness.
    """
    REQUIREMENT_TYPE_CHOICES = [
        ('COVER_LETTER', 'Cover Letter'),
        ('ETHICS_STATEMENT', 'Ethics Statement'),
        ('FUNDING_INFORMATION', 'Funding Information'),
        ('CONFLICT_OF_INTEREST', 'Conflict of Interest Declaration'),
        ('DATA_AVAILABILITY', 'Data Availability Statement'),
        ('AUTHOR_CONTRIBUTIONS', 'Author Contributions'),
        ('SUPPLEMENTARY_MATERIALS', 'Supplementary Materials'),
        ('COPYRIGHT_FORM', 'Copyright Form'),
    ]
    
    STATUS_CHOICES = [
        ('REQUIRED', 'Required'),
        ('PROVIDED', 'Provided'),
        ('NOT_APPLICABLE', 'Not Applicable'),
        ('PENDING_REVIEW', 'Pending Review'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Check target
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='requirement_checks'
    )
    
    # Requirement details
    requirement_type = models.CharField(max_length=30, choices=REQUIREMENT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REQUIRED')
    
    # Requirement fulfillment
    is_fulfilled = models.BooleanField(default=False)
    fulfillment_details = models.JSONField(
        default=dict,
        help_text="Details about how the requirement was fulfilled"
    )
    
    # Associated documents or data
    related_documents = models.ManyToManyField(
        'submissions.DocumentVersion',
        blank=True,
        related_name='requirement_checks'
    )
    
    # Review and validation
    reviewed_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_requirements'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['submission', 'requirement_type']
        ordering = ['requirement_type']
        indexes = [
            models.Index(fields=['submission', 'status']),
            models.Index(fields=['requirement_type', 'is_fulfilled']),
            models.Index(fields=['reviewed_by']),
        ]
    
    def __str__(self):
        return f"{self.get_requirement_type_display()} for {self.submission.title[:30]}... ({self.get_status_display()})"
