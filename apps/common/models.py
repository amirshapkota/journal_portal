"""
Common models for the Journal Portal.
Shared models for audit logging, verification, concepts, embeddings, etc.
"""
import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class ActivityLog(models.Model):
    """
    Audit log model for tracking all system activities.
    """
    ACTION_TYPE_CHOICES = [
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('SUBMIT', 'Submit'),
        ('REVIEW', 'Review'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('PUBLISH', 'Publish'),
        ('WITHDRAW', 'Withdraw'),
    ]
    
    ACTOR_TYPE_CHOICES = [
        ('USER', 'User'),
        ('SYSTEM', 'System'),
        ('API', 'API'),
        ('INTEGRATION', 'Integration'),
    ]
    
    RESOURCE_TYPE_CHOICES = [
        ('USER', 'User'),
        ('PROFILE', 'Profile'),
        ('SUBMISSION', 'Submission'),
        ('DOCUMENT', 'Document'),
        ('REVIEW', 'Review'),
        ('JOURNAL', 'Journal'),
        ('PLAGIARISM_REPORT', 'Plagiarism Report'),
        ('FORMAT_CHECK', 'Format Check'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Actor information
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs'
    )
    actor_type = models.CharField(max_length=20, choices=ACTOR_TYPE_CHOICES)
    
    # Action details
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES)
    resource_type = models.CharField(max_length=30, choices=RESOURCE_TYPE_CHOICES)
    resource_id = models.CharField(max_length=100, help_text="ID of the affected resource")
    
    # Additional context
    metadata = models.JSONField(
        default=dict,
        help_text="Additional context and details about the action"
    )
    
    # Request information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=100, blank=True)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action_type', 'resource_type']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        actor = self.user.email if self.user else f"({self.actor_type})"
        return f"{actor} {self.action_type} {self.resource_type} {self.resource_id}"


class VerificationTicket(models.Model):
    """
    Verification ticket for user role requests and identity verification.
    """
    REQUESTED_ROLE_CHOICES = [
        ('AUTHOR', 'Author'),
        ('REVIEWER', 'Reviewer'),
        ('EDITOR', 'Editor'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('REQUIRES_MORE_INFO', 'Requires More Information'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Ticket details
    profile = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='verification_tickets'
    )
    requested_role = models.CharField(max_length=20, choices=REQUESTED_ROLE_CHOICES)
    
    # Evidence and documentation
    evidence = models.JSONField(
        default=dict,
        help_text="Supporting evidence for the verification request"
    )
    supporting_documents = models.ManyToManyField(
        'submissions.DocumentVersion',
        blank=True,
        related_name='verification_tickets'
    )
    
    # ML scoring
    ml_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="ML-generated verification score (0-1)"
    )
    ml_reasoning = models.JSONField(
        default=dict,
        help_text="ML reasoning and confidence factors"
    )
    
    # Review and decision
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reviewed_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_verification_tickets'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['profile', 'status']),
            models.Index(fields=['requested_role', 'status']),
            models.Index(fields=['reviewed_by']),
            models.Index(fields=['ml_score']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Verification request for {self.profile} - {self.get_requested_role_display()}"


class Concept(models.Model):
    """
    Concept/Topic model for expertise areas and research topics.
    """
    PROVIDER_CHOICES = [
        ('OPENALEX', 'OpenAlex'),
        ('CUSTOM', 'Custom'),
        ('MANUAL', 'Manual'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Concept information
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Provider and external IDs
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    external_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="External provider's concept ID"
    )
    
    # Hierarchy and relationships
    parent_concept = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_concepts'
    )
    related_concepts = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=True
    )
    
    # Concept metadata
    metadata = models.JSONField(
        default=dict,
        help_text="Additional concept metadata and properties"
    )
    
    # Embedding reference
    embedding = models.OneToOneField(
        'Embedding',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='concept'
    )
    
    # Usage statistics
    usage_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['provider', 'external_id']
        ordering = ['name']
        indexes = [
            models.Index(fields=['provider', 'external_id']),
            models.Index(fields=['parent_concept']),
            models.Index(fields=['usage_count']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name


class Embedding(models.Model):
    """
    Embedding model for storing vector representations.
    """
    TYPE_CHOICES = [
        ('DOCUMENT', 'Document'),
        ('PROFILE', 'Profile'),
        ('CONCEPT', 'Concept'),
        ('SUBMISSION', 'Submission'),
        ('REVIEW', 'Review'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Embedding metadata
    embedding_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    source_id = models.CharField(
        max_length=100,
        help_text="ID of the source object this embedding represents"
    )
    
    # Vector information
    vector_dimensions = models.PositiveIntegerField()
    model_name = models.CharField(
        max_length=100,
        help_text="Name of the model used to generate the embedding"
    )
    model_version = models.CharField(max_length=50, blank=True)
    
    # Embedding storage
    # Note: In production, vectors would typically be stored in a vector database
    # This is for reference/metadata only
    vector_hash = models.CharField(
        max_length=64,
        help_text="Hash of the vector for deduplication"
    )
    
    # External storage reference
    vector_store_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="ID in external vector store (e.g., Pinecone, Weaviate)"
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        help_text="Additional embedding metadata"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['embedding_type', 'source_id', 'model_name']
        indexes = [
            models.Index(fields=['embedding_type', 'source_id']),
            models.Index(fields=['vector_hash']),
            models.Index(fields=['model_name', 'model_version']),
            models.Index(fields=['vector_store_id']),
        ]
    
    def __str__(self):
        return f"{self.embedding_type} embedding for {self.source_id}"


class AnomalyEvent(models.Model):
    """
    Anomaly detection events for identifying suspicious activities.
    """
    EVENT_TYPE_CHOICES = [
        ('UNUSUAL_SUBMISSION_PATTERN', 'Unusual Submission Pattern'),
        ('SUSPICIOUS_REVIEWER_BEHAVIOR', 'Suspicious Reviewer Behavior'),
        ('RAPID_ACCEPTANCE', 'Rapid Acceptance'),
        ('CITATION_MANIPULATION', 'Citation Manipulation'),
        ('DUPLICATE_CONTENT', 'Duplicate Content'),
        ('FAKE_PEER_REVIEW', 'Fake Peer Review'),
        ('AUTHORSHIP_ISSUES', 'Authorship Issues'),
        ('UNUSUAL_REFERENCE_PATTERN', 'Unusual Reference Pattern'),
    ]
    
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Event details
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    
    # Resource reference
    resource_type = models.CharField(max_length=30)
    resource_id = models.CharField(max_length=100)
    
    # Anomaly scoring
    anomaly_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Anomaly score (0-1, higher = more anomalous)"
    )
    
    # Evidence and reasoning
    evidence = models.JSONField(
        default=dict,
        help_text="Evidence and reasoning for the anomaly detection"
    )
    
    # Detection metadata
    detector_name = models.CharField(max_length=100)
    detector_version = models.CharField(max_length=50, blank=True)
    detection_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Confidence in the detection (0-1)"
    )
    
    # Handling and resolution
    is_handled = models.BooleanField(default=False)
    handled_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_anomalies'
    )
    handled_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # False positive tracking
    is_false_positive = models.BooleanField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-anomaly_score', '-created_at']
        indexes = [
            models.Index(fields=['event_type', 'severity']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['anomaly_score']),
            models.Index(fields=['is_handled', 'severity']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.get_severity_display()} ({self.anomaly_score:.2f})"


class Award(models.Model):
    """
    Award/Badge model for recognizing user achievements.
    """
    BADGE_TYPE_CHOICES = [
        ('QUALITY_REVIEWER', 'Quality Reviewer'),
        ('FAST_REVIEWER', 'Fast Reviewer'),
        ('PROLIFIC_AUTHOR', 'Prolific Author'),
        ('HELPFUL_EDITOR', 'Helpful Editor'),
        ('CITATION_CHAMPION', 'Citation Champion'),
        ('OPEN_SCIENCE_ADVOCATE', 'Open Science Advocate'),
        ('PEER_REVIEW_EXPERT', 'Peer Review Expert'),
        ('RESEARCH_INTEGRITY', 'Research Integrity'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Award recipient
    profile = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='awards'
    )
    
    # Award details
    badge_type = models.CharField(max_length=30, choices=BADGE_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Award criteria and evidence
    criteria_met = models.JSONField(
        default=dict,
        help_text="Criteria that were met to earn this award"
    )
    evidence = models.JSONField(
        default=dict,
        help_text="Evidence supporting the award"
    )
    
    # Award metadata
    points_value = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True)
    
    # Award granting
    awarded_by = models.ForeignKey(
        'users.Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_awards'
    )
    auto_awarded = models.BooleanField(
        default=True,
        help_text="Whether this award was automatically granted by the system"
    )
    
    # Timestamps
    awarded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-awarded_at']
        indexes = [
            models.Index(fields=['profile', 'badge_type']),
            models.Index(fields=['badge_type', 'awarded_at']),
            models.Index(fields=['is_public']),
        ]
    
    def __str__(self):
        return f"{self.get_badge_type_display()} awarded to {self.profile}"


# Add the expertise areas relationship to Profile
# This will be handled in a migration after the Concept model is created
