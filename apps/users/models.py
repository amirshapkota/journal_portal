"""
User models for the Journal Portal.
Handles authentication, user profiles, and role management.
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.core.validators import EmailValidator
from cryptography.fernet import Fernet
from django.conf import settings


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
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
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
