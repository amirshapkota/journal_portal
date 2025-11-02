"""
Django signals for the users app.

Handles automatic profile creation and other user-related events.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import CustomUser, Profile, Role


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a Profile when a new user is created.
    
    This ensures every user has an associated profile for extended information.
    Also assigns the default 'READER' role to new users.
    """
    if created:
        profile = Profile.objects.create(
            user=instance,
            display_name=f"{instance.first_name} {instance.last_name}".strip()
        )
        
        # Assign default READER role to new users
        try:
            reader_role = Role.objects.get(name='READER')
            profile.roles.add(reader_role)
        except Role.DoesNotExist:
            # If READER role doesn't exist, create it
            reader_role = Role.objects.create(
                name='READER',
                description='Default role for registered users with read access'
            )
            profile.roles.add(reader_role)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    """
    Update the profile's display name when user info changes.
    
    This keeps the display name in sync with the user's first/last name.
    """
    if hasattr(instance, 'profile'):
        # Update display name if it's empty or default
        current_display = f"{instance.first_name} {instance.last_name}".strip()
        if not instance.profile.display_name or instance.profile.display_name == current_display:
            instance.profile.display_name = current_display
            instance.profile.save()