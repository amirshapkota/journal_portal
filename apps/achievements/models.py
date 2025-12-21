"""
Models for achievements, badges, awards, and leaderboards.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Badge(models.Model):
    """
    Badge model for reviewer/author achievements.
    """
    BADGE_TYPE_CHOICES = [
        ('REVIEWER', 'Reviewer Badge'),
        ('AUTHOR', 'Author Badge'),
        ('EDITOR', 'Editor Badge'),
        ('CONTRIBUTOR', 'Contributor Badge'),
    ]
    
    BADGE_LEVEL_CHOICES = [
        ('BRONZE', 'Bronze'),
        ('SILVER', 'Silver'),
        ('GOLD', 'Gold'),
        ('PLATINUM', 'Platinum'),
        ('DIAMOND', 'Diamond'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    badge_type = models.CharField(max_length=50, choices=BADGE_TYPE_CHOICES)
    level = models.CharField(max_length=20, choices=BADGE_LEVEL_CHOICES, default='BRONZE')
    
    # Badge criteria
    criteria = models.JSONField(
        default=dict,
        help_text="Criteria for earning this badge (e.g., {'reviews_completed': 10})"
    )
    
    # Icon/Image
    icon_url = models.URLField(blank=True, null=True)
    icon_color = models.CharField(max_length=7, default='#FFD700')  # Hex color
    
    # Points value
    points = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['badge_type', 'level', 'name']
        indexes = [
            models.Index(fields=['badge_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"


class UserBadge(models.Model):
    """
    User's earned badges.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    profile = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='badges'
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name='user_badges'
    )
    
    earned_at = models.DateTimeField(auto_now_add=True)
    year = models.IntegerField(default=timezone.now().year)
    
    # Optional association with journal or submission
    journal = models.ForeignKey(
        'journals.Journal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='awarded_badges'
    )
    
    # Achievement details
    achievement_data = models.JSONField(
        default=dict,
        help_text="Data about how the badge was earned"
    )
    
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-earned_at']
        indexes = [
            models.Index(fields=['profile', '-earned_at']),
            models.Index(fields=['badge', 'year']),
        ]
    
    def __str__(self):
        return f"{self.profile.display_name} - {self.badge.name}"


class Award(models.Model):
    """
    Annual awards for best reviewer, researcher of the year, etc.
    """
    AWARD_TYPE_CHOICES = [
        ('BEST_REVIEWER', 'Best Reviewer'),
        ('RESEARCHER_OF_YEAR', 'Researcher of the Year'),
        ('TOP_CONTRIBUTOR', 'Top Contributor'),
        ('EXCELLENCE_REVIEW', 'Excellence in Review'),
        ('RISING_STAR', 'Rising Star'),
        ('LIFETIME_ACHIEVEMENT', 'Lifetime Achievement'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    award_type = models.CharField(max_length=50, choices=AWARD_TYPE_CHOICES)
    
    year = models.IntegerField()
    
    # Scope
    journal = models.ForeignKey(
        'journals.Journal',
        on_delete=models.CASCADE,
        related_name='awards',
        null=True,
        blank=True,
        help_text="If null, award is global"
    )
    
    # Filtering by discipline/country
    discipline = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Winner
    recipient = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='awards_received'
    )
    
    # Award details
    citation = models.TextField(blank=True)
    metrics = models.JSONField(
        default=dict,
        help_text="Metrics that led to the award"
    )
    
    # Certificate
    certificate_generated = models.BooleanField(default=False)
    certificate_url = models.URLField(blank=True, null=True)
    
    announced_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-year', '-announced_at']
        indexes = [
            models.Index(fields=['year', 'award_type']),
            models.Index(fields=['journal', 'year']),
            models.Index(fields=['recipient']),
        ]
        unique_together = [
            ['journal', 'award_type', 'year', 'discipline', 'country']
        ]
    
    def __str__(self):
        scope = f"{self.journal.short_name} - " if self.journal else "Global - "
        return f"{scope}{self.title} {self.year} - {self.recipient.display_name}"


class Leaderboard(models.Model):
    """
    Leaderboard entries for rankings by field/country.
    """
    CATEGORY_CHOICES = [
        ('REVIEWER', 'Top Reviewers'),
        ('AUTHOR', 'Top Authors'),
        ('CITATIONS', 'Most Cited'),
        ('CONTRIBUTIONS', 'Top Contributors'),
    ]
    
    PERIOD_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
        ('ALL_TIME', 'All Time'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    profile = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='leaderboard_entries'
    )
    
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    
    # Scope
    journal = models.ForeignKey(
        'journals.Journal',
        on_delete=models.CASCADE,
        related_name='leaderboard_entries',
        null=True,
        blank=True
    )
    field = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Ranking data
    rank = models.IntegerField(validators=[MinValueValidator(1)])
    score = models.FloatField(validators=[MinValueValidator(0)])
    
    # Metrics
    metrics = models.JSONField(
        default=dict,
        help_text="Detailed metrics for the ranking"
    )
    
    # Period dates
    period_start = models.DateField()
    period_end = models.DateField()
    
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['period_end', 'category', 'rank']
        indexes = [
            models.Index(fields=['category', 'period', '-score']),
            models.Index(fields=['journal', 'category', 'period']),
            models.Index(fields=['field', 'category', 'period']),
            models.Index(fields=['country', 'category', 'period']),
        ]
        unique_together = [
            ['profile', 'category', 'period', 'period_start', 'period_end', 'journal', 'field', 'country']
        ]
    
    def __str__(self):
        return f"#{self.rank} - {self.profile.display_name} ({self.category})"


class Certificate(models.Model):
    """
    Certificates for awards and achievements.
    """
    CERTIFICATE_TYPE_CHOICES = [
        ('AWARD', 'Award Certificate'),
        ('BADGE', 'Badge Certificate'),
        ('RECOGNITION', 'Recognition Certificate'),
        ('PARTICIPATION', 'Participation Certificate'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    recipient = models.ForeignKey(
        'users.Profile',
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    
    certificate_type = models.CharField(max_length=50, choices=CERTIFICATE_TYPE_CHOICES)
    title = models.CharField(max_length=300)
    description = models.TextField()
    
    # Association
    award = models.ForeignKey(
        Award,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='certificates'
    )
    badge = models.ForeignKey(
        UserBadge,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='certificates'
    )
    
    journal = models.ForeignKey(
        'journals.Journal',
        on_delete=models.CASCADE,
        related_name='certificates_issued',
        null=True,
        blank=True
    )
    
    # Certificate data
    certificate_number = models.CharField(max_length=50, unique=True)
    issued_date = models.DateField(default=timezone.now)
    
    # Generated file
    file_url = models.URLField(blank=True, null=True)
    pdf_generated = models.BooleanField(default=False)
    
    # Template and styling
    template_name = models.CharField(max_length=100, default='default')
    custom_data = models.JSONField(
        default=dict,
        help_text="Additional data for certificate generation"
    )
    
    # Verification
    verification_code = models.CharField(max_length=100, unique=True)
    is_public = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-issued_date']
        indexes = [
            models.Index(fields=['recipient', '-issued_date']),
            models.Index(fields=['verification_code']),
            models.Index(fields=['certificate_number']),
        ]
    
    def __str__(self):
        return f"{self.certificate_number} - {self.recipient.display_name}"
    
    def generate_certificate_number(self):
        """Generate unique certificate number."""
        from datetime import datetime
        prefix = self.certificate_type[0]
        year = datetime.now().year
        count = Certificate.objects.filter(
            certificate_type=self.certificate_type,
            issued_date__year=year
        ).count() + 1
        return f"{prefix}{year}{count:05d}"
    
    def generate_verification_code(self):
        """Generate verification code."""
        import hashlib
        import secrets
        data = f"{self.id}{self.recipient.id}{secrets.token_hex(8)}"
        return hashlib.sha256(data.encode()).hexdigest()[:20].upper()
    
    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.certificate_number = self.generate_certificate_number()
        if not self.verification_code:
            self.verification_code = self.generate_verification_code()
        super().save(*args, **kwargs)
