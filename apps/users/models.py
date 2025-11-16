"""
User models for the Journal Portal.
Handles authentication, user profiles, and role management.
"""
import uuid
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.core.validators import EmailValidator
from cryptography.fernet import Fernet
from django.conf import settings


class CustomUserManager(UserManager):
    """Custom user manager that uses email instead of username."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Uses UUID as primary key and email as username.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        help_text="Unique email address for authentication"
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        null=True,
        blank=True,
        help_text="Optional username, defaults to email"
    )
    
    # Override default fields
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        app_label = 'users'
        db_table = 'auth_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.email


class Role(models.Model):
    """
    Roles that users can have in the system.
    """
    ROLE_CHOICES = [
        ('READER', 'Reader'),
        ('AUTHOR', 'Author'),
        ('REVIEWER', 'Reviewer'),
        ('EDITOR', 'Editor'),
        ('ADMIN', 'Administrator'),
    ]
    
    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=dict, help_text="Role-specific permissions")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.get_name_display()


class Profile(models.Model):
    """
    Extended user profile with academic and verification information.
    """
    VERIFICATION_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('GENUINE', 'Genuine'),
        ('SUSPICIOUS', 'Suspicious'),
        ('UNCLEAR', 'Unclear'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Display information
    display_name = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    # ORCID integration
    orcid_id = models.CharField(
        max_length=19,
        unique=True,
        null=True,
        blank=True,
        help_text="ORCID identifier (e.g., 0000-0000-0000-0000)"
    )
    orcid_token_encrypted = models.BinaryField(
        null=True,
        blank=True,
        help_text="Encrypted ORCID access token"
    )
    
    # Affiliation information
    affiliation_ror_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Research Organization Registry (ROR) ID"
    )
    affiliation_name = models.CharField(max_length=255, blank=True)
    
    # OpenAlex integration
    openalex_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="OpenAlex author ID"
    )
    
    # Roles and verification
    roles = models.ManyToManyField(Role, blank=True, related_name='profiles')
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='PENDING'
    )
    verification_meta = models.JSONField(
        default=dict,
        help_text="Verification scores, evidence, and metadata"
    )
    
    # Expertise areas
    expertise_areas = models.ManyToManyField(
        'common.Concept',
        blank=True,
        related_name='experts',
        help_text="Research areas and expertise of the user"
    )
    
    # OJS Integration (user IDs are journal-specific in OJS)
    # We store mapping as JSON: {"journal_id_1": ojs_user_id_1, "journal_id_2": ojs_user_id_2}
    ojs_id_mapping = models.JSONField(
        default=dict,
        blank=True,
        help_text="Map of journal ID to OJS user ID: {'journal_uuid': ojs_user_id}"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['orcid_id']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['affiliation_ror_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.display_name or self.user.email
    
    def get_full_name(self):
        """Return the full name or display name."""
        if self.display_name:
            return self.display_name
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.email
    
    def encrypt_orcid_token(self, token):
        """Encrypt ORCID token before storage."""
        if token:
            # In production, use a proper key management system
            import base64
            key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].encode().ljust(32, b'0')[:32])
            f = Fernet(key)
            self.orcid_token_encrypted = f.encrypt(token.encode())
    
    def decrypt_orcid_token(self):
        """Decrypt ORCID token for use."""
        if self.orcid_token_encrypted:
            import base64
            key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].encode().ljust(32, b'0')[:32])
            f = Fernet(key)
            return f.decrypt(self.orcid_token_encrypted).decode()
        return None
    
    def has_role(self, role_name):
        """Check if profile has a specific role."""
        return self.roles.filter(name=role_name).exists()
    
    def is_verified(self):
        """Check if the profile is verified as genuine."""
        return self.verification_status == 'GENUINE'


class VerificationRequest(models.Model):
    """
    Identity verification request model for authors and reviewers.
    Tracks verification requests with ORCID integration and admin review.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('INFO_REQUESTED', 'Additional Information Requested'),
        ('WITHDRAWN', 'Withdrawn by User'),
    ]
    
    ROLE_CHOICES = [
        ('AUTHOR', 'Author'),
        ('REVIEWER', 'Reviewer'),
        ('EDITOR', 'Editor'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User reference
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='verification_requests',
        help_text="User profile requesting verification"
    )
    
    # Request details
    requested_roles = ArrayField(
        models.CharField(max_length=20, choices=ROLE_CHOICES),
        default=list,
        help_text="Roles being requested for verification (e.g., ['AUTHOR', 'REVIEWER'])"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Current status of verification request"
    )
    
    # User-provided information
    affiliation = models.CharField(
        max_length=255,
        help_text="Current institutional affiliation"
    )
    affiliation_email = models.EmailField(
        validators=[EmailValidator()],
        help_text="Institutional email address"
    )
    research_interests = models.TextField(
        blank=True,
        help_text="Research interests and expertise areas"
    )
    academic_position = models.CharField(
        max_length=100,
        blank=True,
        help_text="Current academic position (e.g., Professor, PhD Student)"
    )
    
    # Supporting letter from supervisor/institution
    supporting_letter = models.TextField(
        blank=True,
        help_text="Letter from supervisor or institution supporting the verification request"
    )
    
    # ORCID integration
    orcid_verified = models.BooleanField(
        default=False,
        help_text="Whether ORCID is connected and verified"
    )
    orcid_id = models.CharField(
        max_length=19,
        blank=True,
        help_text="ORCID iD at time of request"
    )
    
    # Automated scoring (rule-based heuristics)
    auto_score = models.IntegerField(
        default=0,
        help_text="Automated verification score (0-100)"
    )
    score_details = models.JSONField(
        default=dict,
        help_text="Breakdown of scoring factors"
    )
    
    # Admin review
    reviewed_by = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_verifications',
        help_text="Admin who reviewed this request"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the request was reviewed"
    )
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal notes from admin review"
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection (shown to user)"
    )
    additional_info_requested = models.TextField(
        blank=True,
        help_text="Additional information requested from user"
    )
    
    # User response to info request
    user_response = models.TextField(
        blank=True,
        help_text="User's response to additional info request"
    )
    user_response_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user responded to info request"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['profile', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['reviewed_by', 'status']),
            models.Index(fields=['auto_score']),
        ]
    
    def __str__(self):
        roles = ', '.join(self.requested_roles) if self.requested_roles else 'No roles'
        return f"Verification request for {self.profile.user.email} - {roles} ({self.status})"
    
    def calculate_auto_score(self):
        """
        Calculate automated verification score based on heuristics.
        No ML - just rule-based scoring.
        """
        score = 0
        details = {}
        
        # ORCID verification (30 points)
        if self.orcid_verified and self.orcid_id:
            score += 30
            details['orcid'] = 30
        else:
            details['orcid'] = 0
        
        # Institutional email (25 points)
        email_domain = self.affiliation_email.split('@')[-1].lower()
        institutional_domains = ['edu', 'ac.uk', 'ac.in', 'edu.au', 'ac.jp', 'edu.cn']
        if any(domain in email_domain for domain in institutional_domains):
            score += 25
            details['institutional_email'] = 25
        else:
            details['institutional_email'] = 0
        
        # Email domain matches affiliation (15 points)
        if self.affiliation and email_domain in self.affiliation.lower().replace(' ', ''):
            score += 15
            details['email_affiliation_match'] = 15
        else:
            details['email_affiliation_match'] = 0
        
        # Research interests provided (10 points)
        if self.research_interests and len(self.research_interests) > 50:
            score += 10
            details['research_interests'] = 10
        else:
            details['research_interests'] = 0
        
        # Academic position provided (10 points)
        if self.academic_position:
            score += 10
            details['academic_position'] = 10
        else:
            details['academic_position'] = 0
        
        # Supporting letter (10 points)
        if self.supporting_letter and len(self.supporting_letter) > 100:
            score += 10
            details['supporting_letter'] = 10
        else:
            details['supporting_letter'] = 0
        
        self.auto_score = score
        self.score_details = details
        return score
