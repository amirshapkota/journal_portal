import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from apps.submissions.copyediting_models import CopyeditingAssignment
from django.contrib.auth import get_user_model

User = get_user_model()

# Get the assignment
assignment_id = '65901d68-7366-4bea-b70f-8bd088da1b90'

try:
    assignment = CopyeditingAssignment.objects.select_related(
        'copyeditor__user', 'assigned_by__user', 'submission__journal'
    ).get(id=assignment_id)
    
    print("=" * 80)
    print("ASSIGNMENT TARGET USER")
    print("=" * 80)
    
    # Find user with email amir@omwaytech.com
    target_user = User.objects.filter(email='amir@omwaytech.com').first()
    
    if target_user:
        print(f"\nUser Found: {target_user.email}")
        print(f"User ID: {target_user.id}")
        print(f"Has Profile: {hasattr(target_user, 'profile')}")
        
        if hasattr(target_user, 'profile'):
            print(f"Profile ID: {target_user.profile.id}")
            print(f"\nPermission Checks:")
            print(f"  - Is Superuser: {target_user.is_superuser}")
            print(f"  - Is Staff: {target_user.is_staff}")
            print(f"  - Profile == Copyeditor: {target_user.profile.id == assignment.copyeditor.id}")
            print(f"  - Profile == Assigned By: {target_user.profile.id == assignment.assigned_by.id}")
            
            # Check journal staff
            from apps.journals.models import JournalStaff
            is_journal_staff = JournalStaff.objects.filter(
                journal=assignment.submission.journal,
                profile=target_user.profile,
                is_active=True
            ).exists()
            print(f"  - Is Journal Staff: {is_journal_staff}")
            
            print(f"\nExpected Profile IDs:")
            print(f"  - Copyeditor ID: {assignment.copyeditor.id}")
            print(f"  - Assigned By ID: {assignment.assigned_by.id}")
            print(f"  - User's Profile ID: {target_user.profile.id}")
            
            # Simulate permission check
            print(f"\n{'=' * 80}")
            print("PERMISSION SIMULATION")
            print("=" * 80)
            
            allowed = False
            reason = None
            
            if target_user.is_superuser or target_user.is_staff:
                allowed = True
                reason = "User is superuser or staff"
            elif is_journal_staff:
                allowed = True
                reason = "User is active journal staff"
            elif target_user.profile.id == assignment.copyeditor.id:
                allowed = True
                reason = "User is the assigned copyeditor"
            elif target_user.profile.id == assignment.assigned_by.id:
                allowed = True
                reason = "User is the assigner (assigned_by)"
            else:
                reason = "User does not meet any permission criteria"
            
            print(f"Permission Granted: {allowed}")
            print(f"Reason: {reason}")
        else:
            print("User has NO profile!")
    else:
        print("User with email amir@omwaytech.com not found!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
