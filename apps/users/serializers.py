"""
Serializers for user authentication and management.

Provides comprehensive serialization for user registration, profile management,
role assignment, and authentication workflows with ORCID integration.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import CustomUser, Profile, Role
import re
import uuid


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional user information."""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user) 
        
        # Add custom claims
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        # Check if user has a profile and get verification status and roles
        is_verified = False
        roles = []
        if hasattr(user, 'profile'):
            is_verified = user.profile.verification_status == 'GENUINE'
            roles = list(user.profile.roles.values_list('name', flat=True))
            
            # # Add EDITOR role if user is a journal staff member
            # from apps.journals.models import JournalStaff
            # if JournalStaff.objects.filter(profile=user.profile, is_active=True).exists():
            #     if 'EDITOR' not in roles:
            #         roles.append('EDITOR')
        
        token['is_verified'] = is_verified
        token['roles'] = roles
        
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add extra user information to response
        user = self.user
        is_verified = False
        roles = []
        if hasattr(user, 'profile'):
            is_verified = user.profile.verification_status == 'GENUINE'
            # Get user roles as an array
            roles = list(user.profile.roles.values_list('name', flat=True))
            
            # Add EDITOR role if user is a journal staff member
            from apps.journals.models import JournalStaff
            if JournalStaff.objects.filter(profile=user.profile, is_active=True).exists():
                if 'EDITOR' not in roles:
                    roles.append('EDITOR')
            
        data.update({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_verified': is_verified,
                'roles': roles,
                'date_joined': user.date_joined,
            }
        })
        
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration with validation."""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = (
            'email', 'first_name', 'last_name', 'password', 'password_confirm'
        )
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_email(self, value):
        """Validate email format and uniqueness."""
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise serializers.ValidationError("Enter a valid email address.")
        
        return value

    def validate(self, attrs):
        """Validate password confirmation and strength."""
        password = attrs.get('password')
        password_confirm = attrs.pop('password_confirm', None)
        
        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': 'Password confirmation does not match.'
            })
        
        # Validate password strength
        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})
        
        return attrs

    def create(self, validated_data):
        """Create user with encrypted password."""
        validated_data.pop('password_confirm', None)
        user = CustomUser.objects.create_user(**validated_data)
        return user


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile information."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    expertise_areas = serializers.SerializerMethodField()
    
    def get_expertise_areas(self, obj):
        """Convert Concept objects to list of names for GET requests."""
        if obj.expertise_areas.exists():
            return list(obj.expertise_areas.values_list('name', flat=True))
        return []
    
    class Meta:
        model = Profile
        fields = (
            'id', 'user_email', 'user_name', 'display_name', 'bio', 'avatar',
            'orcid_id', 'affiliation_ror_id', 'affiliation_name', 'openalex_id',
            'verification_status', 'verification_meta', 'expertise_areas',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'verification_status', 'verification_meta')

    def get_user_name(self, obj):
        """Get user's full name."""
        return f"{obj.user.first_name} {obj.user.last_name}"

    def validate_orcid_id(self, value):
        """Validate ORCID ID format."""
        if value:
            orcid_pattern = r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$'
            if not re.match(orcid_pattern, value):
                raise serializers.ValidationError(
                    "ORCID ID must be in format: 0000-0000-0000-0000"
                )
        return value
    
    def validate(self, attrs):
        """Custom validation including expertise_areas."""
        # Handle expertise_areas from initial data
        if 'expertise_areas' in self.initial_data:
            expertise_areas = self.initial_data.get('expertise_areas')
            if expertise_areas is not None:
                if not isinstance(expertise_areas, list):
                    raise serializers.ValidationError({
                        'expertise_areas': 'Must be a list of strings.'
                    })
                # Validate each item is a string
                for item in expertise_areas:
                    if not isinstance(item, str):
                        raise serializers.ValidationError({
                            'expertise_areas': 'All items must be strings.'
                        })
                attrs['expertise_areas'] = expertise_areas
        return attrs
    
    def update(self, instance, validated_data):
        """Update profile with proper handling of expertise areas."""
        # Import here to avoid circular imports
        from apps.common.models import Concept
        
        # Extract expertise_areas before updating other fields
        expertise_areas_data = validated_data.pop('expertise_areas', None)
        
        # Update regular fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update expertise areas if provided
        if expertise_areas_data is not None:
            concept_objects = []
            for concept_name in expertise_areas_data:
                if concept_name and concept_name.strip():
                    # Try to find existing concept by name first
                    try:
                        concept = Concept.objects.get(
                            name=concept_name.strip(),
                            provider='MANUAL'
                        )
                    except Concept.DoesNotExist:
                        # Create new concept with unique external_id
                        concept = Concept.objects.create(
                            name=concept_name.strip(),
                            provider='MANUAL',
                            external_id=str(uuid.uuid4())
                        )
                    concept_objects.append(concept)
            
            # Set the many-to-many relationship
            instance.expertise_areas.set(concept_objects)
        
        return instance


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for user roles."""
    
    class Meta:
        model = Role
        fields = ('id', 'name', 'description', 'permissions', 'created_at')
        read_only_fields = ('id', 'created_at')


class UserSerializer(serializers.ModelSerializer):
    """Comprehensive user serializer with related data."""
    
    profile = ProfileSerializer(read_only=True)
    roles = RoleSerializer(many=True, read_only=True)
    
    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'first_name', 'last_name', 
            'is_active', 'date_joined', 'last_login',
            'profile', 'roles', 'email_verified'
        )
        read_only_fields = (
            'id', 'date_joined', 'last_login', 'email_verified'
        )

    def update(self, instance, validated_data):
        """Update user information."""
        # Don't allow email updates through this serializer
        validated_data.pop('email', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""
    
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        """Validate current password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        """Validate new password confirmation."""
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        if new_password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': 'Password confirmation does not match.'
            })
        
        # Validate password strength
        try:
            validate_password(new_password)
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})
        
        return attrs

    def save(self):
        """Update user password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    
    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate that user exists."""
        try:
            user = CustomUser.objects.get(email=value)
            if not user.is_active:
                raise serializers.ValidationError(
                    "This account is inactive."
                )
        except CustomUser.DoesNotExist:
            # Don't reveal whether user exists for security
            pass
        
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""
    
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate password reset token and new password."""
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        if new_password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': 'Password confirmation does not match.'
            })
        
        # Validate password strength
        try:
            validate_password(new_password)
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})
        
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification."""
    
    token = serializers.CharField()

    def validate_token(self, value):
        """Validate verification token."""
        # Token validation will be handled in the view
        return value