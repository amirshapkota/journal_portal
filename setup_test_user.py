"""
Setup test user for analytics testing.
"""
from apps.users.models import CustomUser, Profile, Role
from django.db import transaction

email = "analytics_test@test.com"
password = "test123456"

try:
    with transaction.atomic():
        # Delete if exists
        CustomUser.objects.filter(email=email).delete()
        
        # Create user
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True
        )
        
        # Create profile
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'display_name': 'Analytics Test User',
                'bio': 'Test user for analytics API',
                'verification_status': 'GENUINE'
            }
        )
        
        # Add ADMIN and EDITOR roles
        admin_role, _ = Role.objects.get_or_create(name='ADMIN')
        editor_role, _ = Role.objects.get_or_create(name='EDITOR')
        profile.roles.add(admin_role, editor_role)
        
        print(f"✓ Created test user: {email}")
        print(f"✓ Password: {password}")
        print(f"✓ Profile: {profile.display_name}")
        print(f"✓ Roles: {', '.join([r.name for r in profile.roles.all()])}")
        
except Exception as e:
    print(f"✗ Error: {str(e)}")
