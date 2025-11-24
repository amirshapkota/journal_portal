"""
Review models for the Journal Portal.
Handles review management, assignments, and recommendations.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta


class ReviewAssignment(models.Model):
    """
    Review assignment model for managing reviewer assignments.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('DECLINED', 'Declined'),
        ('ACCEPTED', 'Accepted'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Assignment details
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='review_assignments'
    )
    reviewer = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='review_assignments'
    )
    assigned_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='assigned_reviews'
    )
    
    # Assignment status and dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    invited_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Assignment details
    invitation_message = models.TextField(blank=True)
    decline_reason = models.TextField(blank=True)
    
    # Review round information
    review_round = models.PositiveIntegerField(default=1)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['submission', 'reviewer', 'review_round']
        indexes = [
            models.Index(fields=['submission', 'status']),
            models.Index(fields=['reviewer', 'status']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['assigned_by']),
        ]
    
    def __str__(self):
        return f"Review assignment for {self.submission.title[:30]}... by {self.reviewer}"
    
    def save(self, *args, **kwargs):
        # Set default due date if not provided
        if not self.due_date:
            # Try to get deadline from journal settings first
            journal = self.submission.journal
            deadline_days = journal.settings.get('review_deadline_days', 30) if journal else 30
            self.due_date = timezone.now() + timedelta(days=deadline_days)
        
        # Track if status changed to ACCEPTED
        is_new = self._state.adding
        old_status = None
        if not is_new:
            try:
                old_instance = ReviewAssignment.objects.get(pk=self.pk)
                old_status = old_instance.status
            except ReviewAssignment.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Update submission status to UNDER_REVIEW when first reviewer accepts
        if old_status == 'PENDING' and self.status == 'ACCEPTED':
            if self.submission.status in ['SUBMITTED', 'REVISED']:
                self.submission.status = 'UNDER_REVIEW'
                self.submission.save()
    
    def is_overdue(self):
        """Check if the review is overdue."""
        return (
            self.status in ['PENDING', 'ACCEPTED'] and
            timezone.now() > self.due_date
        )
    
    def check_and_update_expired(self):
        """Check if assignment has expired and update status if needed."""
        if self.status in ['PENDING', 'ACCEPTED'] and timezone.now() > self.due_date:
            self.status = 'EXPIRED'
            self.save()
            return True
        return False
    
    def days_remaining(self):
        """Calculate days remaining until due date."""
        if self.due_date:
            delta = self.due_date - timezone.now()
            return delta.days
        return None


class ReviewFormTemplate(models.Model):
    """
    Configurable review form templates for journals.
    Allows journals to customize review criteria and scoring.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template identification
    name = models.CharField(max_length=200, help_text="Template name")
    description = models.TextField(blank=True, help_text="Template description")
    
    # Journal relationship (null = system default template)
    journal = models.ForeignKey(
        'journals.Journal',
        on_delete=models.CASCADE,
        related_name='review_templates',
        null=True,
        blank=True,
        help_text="Journal using this template (null for system default)"
    )
    
    # Form configuration (JSON structure defining fields and criteria)
    form_schema = models.JSONField(
        default=dict,
        help_text="JSON schema defining review form fields and validation rules"
    )
    
    # Scoring criteria configuration
    scoring_criteria = models.JSONField(
        default=dict,
        help_text="Scoring criteria configuration (names, weights, ranges)"
    )
    
    # Template status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['journal', 'is_active']),
            models.Index(fields=['is_default']),
        ]
    
    def __str__(self):
        journal_name = self.journal.title if self.journal else "System Default"
        return f"{self.name} ({journal_name})"


class Review(models.Model):
    """
    Review model representing completed reviews.
    """
    RECOMMENDATION_CHOICES = [
        ('ACCEPT', 'Accept'),
        ('MINOR_REVISION', 'Minor Revision'),
        ('MAJOR_REVISION', 'Major Revision'),
        ('REJECT', 'Reject'),
    ]
    
    CONFIDENCE_CHOICES = [
        (1, 'Very Low'),
        (2, 'Low'),
        (3, 'Medium'),
        (4, 'High'),
        (5, 'Very High'),
    ]
    
    REVIEW_TYPE_CHOICES = [
        ('SINGLE_BLIND', 'Single Blind'),  # Reviewer knows author
        ('DOUBLE_BLIND', 'Double Blind'),  # Both anonymous
        ('OPEN', 'Open Review'),  # Both identities known
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Review assignment relationship
    assignment = models.ForeignKey(
        ReviewAssignment,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    # Review details (shortcuts to assignment fields)
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    reviewer = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    # Review timing
    assigned_at = models.DateTimeField()
    due_date = models.DateTimeField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    # Review type and form template
    review_type = models.CharField(
        max_length=20,
        choices=REVIEW_TYPE_CHOICES,
        default='SINGLE_BLIND',
        help_text="Type of review (affects anonymity)"
    )
    form_template = models.ForeignKey(
        ReviewFormTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        help_text="Review form template used"
    )
    
    # Review recommendation and confidence
    recommendation = models.CharField(max_length=20, choices=RECOMMENDATION_CHOICES)
    confidence_level = models.IntegerField(
        choices=CONFIDENCE_CHOICES,
        help_text="Reviewer's confidence in their recommendation"
    )
    
    # Review scores (flexible JSON structure)
    scores = models.JSONField(
        default=dict,
        help_text="Review scores (novelty, methodology, clarity, significance, etc.)"
    )
    
    # Review content
    review_text = models.TextField(help_text="Detailed review comments")
    confidential_comments = models.TextField(
        blank=True,
        help_text="Comments visible only to editors"
    )
    
    # Attached files for review
    attached_files = models.ManyToManyField(
        'submissions.DocumentVersion',
        blank=True,
        related_name='reviews_with_attachments'
    )
    
    # AI-generated summary
    auto_summary = models.TextField(
        blank=True,
        help_text="AI-generated summary of the review"
    )
    
    # Review quality and helpfulness
    quality_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        help_text="Quality score of the review (0-10)"
    )
    
    # Review visibility and status
    is_anonymous = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)  # True by default for new reviews
    
    # Revision round tracking
    review_round = models.PositiveIntegerField(
        default=1,
        help_text="Which revision round this review belongs to (1=initial, 2=first revision, etc.)"
    )
    revision_round = models.ForeignKey(
        'RevisionRound',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        help_text="The revision round this review is for (if applicable)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['submission', 'recommendation']),
            models.Index(fields=['reviewer']),
            models.Index(fields=['submitted_at']),
            models.Index(fields=['assignment']),
            models.Index(fields=['submission', 'review_round']),
            models.Index(fields=['revision_round']),
        ]
    
    def __str__(self):
        return f"Review by {self.reviewer} - {self.get_recommendation_display()}"
    
    def save(self, *args, **kwargs):
        # Copy data from assignment if not set
        if not self.assigned_at and self.assignment:
            self.assigned_at = self.assignment.invited_at
            self.due_date = self.assignment.due_date
            self.submission = self.assignment.submission
            self.reviewer = self.assignment.reviewer
            self.review_round = self.assignment.review_round
        
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        # Update assignment status when review is submitted
        if self.assignment and is_new:
            self.assignment.status = 'COMPLETED'
            self.assignment.completed_at = self.submitted_at
            self.assignment.save()
        
        # Update submission status based on reviewer's recommendation
        # Reviewer sets *_REQUESTED, editor will later set final status
        if is_new and self.submission:
            if self.recommendation in ['MINOR_REVISION', 'MAJOR_REVISION']:
                self.submission.status = 'REVISION_REQUESTED'
            elif self.recommendation == 'ACCEPT':
                self.submission.status = 'ACCEPTANCE_REQUESTED'
            elif self.recommendation == 'REJECT':
                self.submission.status = 'REJECTION_REQUESTED'
            
            self.submission.save()
    
    def get_overall_score(self):
        """Calculate overall score from individual scores."""
        if not self.scores:
            return None
        
        scores = [v for v in self.scores.values() if isinstance(v, (int, float))]
        return sum(scores) / len(scores) if scores else None
    
    def get_review_time_days(self):
        """Calculate how many days the review took."""
        if self.assigned_at and self.submitted_at:
            delta = self.submitted_at - self.assigned_at
            return delta.days
        return None


class ReviewAttachment(models.Model):
    """
    File attachments for reviews (reviewer can attach supporting documents).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Review relationship
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    
    # File details
    file = models.FileField(
        upload_to='review_attachments/%Y/%m/%d/',
        help_text="Attached file (PDF, DOC, DOCX, TXT only)"
    )
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=100)
    
    # Attachment metadata
    description = models.TextField(
        blank=True,
        help_text="Description of the attachment"
    )
    
    # Upload tracking
    uploaded_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='review_attachments'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['review']),
            models.Index(fields=['uploaded_by']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} for review {self.review.id}"
    
    def get_file_extension(self):
        """Get file extension."""
        import os
        return os.path.splitext(self.original_filename)[1].lower()


class ReviewVersion(models.Model):
    """
    Tracks review history and changes (for audit trail).
    Captures snapshots of review content when modified.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Review relationship
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    
    # Version details
    version_number = models.PositiveIntegerField()
    
    # Snapshot of review content
    content_snapshot = models.JSONField(
        help_text="JSON snapshot of review content at this version"
    )
    
    # Change tracking
    changes_made = models.TextField(
        blank=True,
        help_text="Description of changes made in this version"
    )
    changed_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='review_versions'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-version_number', '-created_at']
        unique_together = ['review', 'version_number']
        indexes = [
            models.Index(fields=['review', 'version_number']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Review {self.review.id} - Version {self.version_number}"


class ReviewerRecommendation(models.Model):
    """
    ML-generated reviewer recommendations for submissions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Recommendation target
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='reviewer_recommendations'
    )
    recommended_reviewer = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='reviewer_recommendations'
    )
    
    # Recommendation details
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="ML confidence score (0-1)"
    )
    reasoning = models.JSONField(
        default=dict,
        help_text="Reasoning behind the recommendation (expertise match, etc.)"
    )
    
    # Recommendation source and metadata
    model_version = models.CharField(
        max_length=50,
        help_text="Version of the ML model used"
    )
    generated_by = models.CharField(
        max_length=100,
        default='ml_service',
        help_text="Service that generated this recommendation"
    )
    
    # Recommendation status
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['submission', 'recommended_reviewer']
        ordering = ['-confidence_score', '-created_at']
        indexes = [
            models.Index(fields=['submission', 'confidence_score']),
            models.Index(fields=['recommended_reviewer']),
            models.Index(fields=['is_used']),
        ]
    
    def __str__(self):
        return f"Recommend {self.recommended_reviewer} for {self.submission.title[:30]}... ({self.confidence_score:.2f})"


class EditorialDecision(models.Model):
    """
    Editorial decision model for tracking editorial decisions on submissions.
    Represents the final decision after review process completion.
    """
    DECISION_TYPE_CHOICES = [
        ('ACCEPT', 'Accept'),
        ('REJECT', 'Reject'),
        ('MINOR_REVISION', 'Minor Revision Required'),
        ('MAJOR_REVISION', 'Major Revision Required'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Decision details
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='editorial_decisions'
    )
    decision_type = models.CharField(
        max_length=20,
        choices=DECISION_TYPE_CHOICES,
        help_text="Type of editorial decision"
    )
    
    # Decision maker
    decided_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='editorial_decisions_made',
        help_text="Editor who made the decision"
    )
    
    # Decision content
    decision_letter = models.TextField(
        help_text="Complete decision letter sent to authors"
    )
    confidential_notes = models.TextField(
        blank=True,
        help_text="Internal notes not visible to authors"
    )
    
    # Review aggregation
    reviews_summary = models.JSONField(
        default=dict,
        help_text="Summary of all reviews (recommendations, scores, etc.)"
    )
    
    # Decision metadata
    decision_date = models.DateTimeField(auto_now_add=True)
    
    # Revision deadline (if revision required)
    revision_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Deadline for submitting revised manuscript"
    )
    
    # Decision letter template used
    letter_template = models.ForeignKey(
        'DecisionLetterTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='decisions_using_template'
    )
    
    # Notification tracking
    notification_sent = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-decision_date']
        indexes = [
            models.Index(fields=['submission', 'decision_type']),
            models.Index(fields=['decided_by']),
            models.Index(fields=['decision_date']),
            models.Index(fields=['decision_type', 'decision_date']),
        ]
    
    def __str__(self):
        return f"{self.get_decision_type_display()} - {self.submission.title[:30]}..."
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        # Update submission status based on decision
        if is_new:
            status_mapping = {
                'ACCEPT': 'ACCEPTED',
                'REJECT': 'REJECTED',
                'MINOR_REVISION': 'REVISION_REQUIRED',
                'MAJOR_REVISION': 'REVISION_REQUIRED',
            }
            new_status = status_mapping.get(self.decision_type)
            if new_status:
                self.submission.status = new_status
                self.submission.save()


class RevisionRound(models.Model):
    """
    Tracks revision rounds for manuscripts requiring revisions.
    Manages the workflow from revision request to resubmission.
    """
    STATUS_CHOICES = [
        ('REQUESTED', 'Revision Requested'),
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Revision details
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        related_name='revision_rounds'
    )
    editorial_decision = models.ForeignKey(
        EditorialDecision,
        on_delete=models.CASCADE,
        related_name='revision_rounds',
        help_text="The decision that triggered this revision round"
    )
    
    # Round tracking
    round_number = models.PositiveIntegerField(
        help_text="Revision round number (1, 2, 3...)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='REQUESTED'
    )
    
    # Revision requirements
    revision_requirements = models.TextField(
        help_text="Detailed requirements for revision"
    )
    reviewer_comments_included = models.BooleanField(
        default=True,
        help_text="Whether reviewer comments are shared with authors"
    )
    
    # Deadlines
    requested_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(
        help_text="Deadline for submitting revised manuscript"
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When revised manuscript was submitted"
    )
    
    # Revised documents
    revised_manuscript = models.ForeignKey(
        'submissions.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revision_rounds_as_manuscript',
        help_text="Revised manuscript document"
    )
    response_letter = models.ForeignKey(
        'submissions.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revision_rounds_as_response',
        help_text="Author's response to reviewer comments"
    )
    
    # Author notes
    author_notes = models.TextField(
        blank=True,
        help_text="Author's notes about the revision"
    )
    
    # Reviewer reassignment
    reassigned_reviewers = models.ManyToManyField(
        'users.Profile',
        blank=True,
        related_name='reassigned_revision_rounds',
        help_text="Reviewers reassigned for this revision round"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['submission', 'round_number']
        ordering = ['-round_number', '-created_at']
        indexes = [
            models.Index(fields=['submission', 'round_number']),
            models.Index(fields=['status']),
            models.Index(fields=['deadline']),
            models.Index(fields=['editorial_decision']),
        ]
    
    def __str__(self):
        return f"Revision Round {self.round_number} - {self.submission.title[:30]}..."
    
    def is_overdue(self):
        """Check if the revision is overdue."""
        from django.utils import timezone
        return (
            self.status in ['REQUESTED', 'IN_PROGRESS'] and
            timezone.now() > self.deadline
        )
    
    def check_and_update_expired(self):
        """Check if revision round has expired and update status if needed."""
        if self.status in ['REQUESTED', 'IN_PROGRESS'] and timezone.now() > self.deadline:
            self.status = 'EXPIRED'
            self.save()
            # Update submission status
            self.submission.status = 'REJECTED'
            self.submission.save()
            return True
        return False
    
    def days_remaining(self):
        """Calculate days remaining until deadline."""
        from django.utils import timezone
        if self.deadline:
            delta = self.deadline - timezone.now()
            return delta.days
        return None


class DecisionLetterTemplate(models.Model):
    """
    Templates for decision letters sent to authors.
    Supports variable substitution for personalized letters.
    """
    DECISION_TYPE_CHOICES = [
        ('ACCEPT', 'Accept'),
        ('REJECT', 'Reject'),
        ('MINOR_REVISION', 'Minor Revision'),
        ('MAJOR_REVISION', 'Major Revision'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template identification
    name = models.CharField(
        max_length=200,
        help_text="Template name"
    )
    decision_type = models.CharField(
        max_length=20,
        choices=DECISION_TYPE_CHOICES,
        help_text="Type of decision this template is for"
    )
    
    # Journal association (null = system-wide default)
    journal = models.ForeignKey(
        'journals.Journal',
        on_delete=models.CASCADE,
        related_name='decision_letter_templates',
        null=True,
        blank=True,
        help_text="Journal using this template (null for system default)"
    )
    
    # Template content
    subject = models.CharField(
        max_length=200,
        help_text="Email subject line (supports variables)"
    )
    body = models.TextField(
        help_text="Email body content (HTML supported, supports variables)"
    )
    
    # Template metadata
    description = models.TextField(
        blank=True,
        help_text="Description of this template"
    )
    variables_info = models.JSONField(
        default=dict,
        help_text="Information about available variables (for documentation)"
    )
    
    # Template status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Default template for this decision type"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_decision_templates'
    )
    
    class Meta:
        ordering = ['decision_type', 'name']
        indexes = [
            models.Index(fields=['journal', 'decision_type', 'is_active']),
            models.Index(fields=['is_default', 'decision_type']),
        ]
    
    def __str__(self):
        journal_name = self.journal.title if self.journal else "System Default"
        return f"{self.name} ({self.get_decision_type_display()}) - {journal_name}"
    
    def render(self, context):
        """
        Render template with provided context variables.
        
        Args:
            context (dict): Variables to substitute in template
            
        Returns:
            tuple: (rendered_subject, rendered_body)
        """
        from django.template import Template, Context
        
        subject_template = Template(self.subject)
        body_template = Template(self.body)
        
        django_context = Context(context)
        
        rendered_subject = subject_template.render(django_context)
        rendered_body = body_template.render(django_context)
        
        return rendered_subject, rendered_body
