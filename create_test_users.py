"""Create test users for analytics testing."""
from apps.users.models import CustomUser, Profile, Role
from django.db import transaction

users_to_create = [
    ('author@test.com', 'Test Author', 'AUTHOR'),
    ('reviewer@test.com', 'Test Reviewer', 'REVIEWER'),
]

for email, name, role_name in users_to_create:
    try:
        with transaction.atomic():
            # Delete if exists
            CustomUser.objects.filter(email=email).delete()
            
            # Create user
            user = CustomUser.objects.create_user(
                email=email,
                password='test123456'
            )
            
            # Create profile
            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': name,
                    'verification_status': 'GENUINE'
                }
            )
            
            # Add role
            role, _ = Role.objects.get_or_create(name=role_name)
            profile.roles.add(role)
            
            print(f"✓ Created: {email} ({role_name})")
    except Exception as e:
        print(f"✗ Error creating {email}: {str(e)}")
