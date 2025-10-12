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
            from django.conf import settings
            days = getattr(settings, 'JOURNAL_PORTAL', {}).get('REVIEW_DEADLINE_DAYS', 30)
            self.due_date = timezone.now() + timedelta(days=days)
        
        super().save(*args, **kwargs)
    
    def is_overdue(self):
        """Check if the review is overdue."""
        return (
            self.status in ['PENDING', 'ACCEPTED'] and
            timezone.now() > self.due_date
        )
    
    def days_remaining(self):
        """Calculate days remaining until due date."""
        if self.due_date:
            delta = self.due_date - timezone.now()
            return delta.days
        return None


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
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Review assignment relationship
    assignment = models.OneToOneField(
        ReviewAssignment,
        on_delete=models.CASCADE,
        related_name='review'
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
    is_published = models.BooleanField(default=False)
    
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
        
        super().save(*args, **kwargs)
        
        # Update assignment status
        if self.assignment:
            self.assignment.status = 'COMPLETED'
            self.assignment.completed_at = self.submitted_at
            self.assignment.save()
    
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
