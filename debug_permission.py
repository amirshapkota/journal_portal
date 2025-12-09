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
        'copyeditor', 'assigned_by', 'submission', 'submission__journal'
    ).get(id=assignment_id)
    
    print("=" * 80)
    print("ASSIGNMENT DETAILS")
    print("=" * 80)
    print(f"Assignment ID: {assignment.id}")
    print(f"Submission: {assignment.submission.title}")
    print(f"Status: {assignment.status}")
    print(f"\nCopyeditor ID: {assignment.copyeditor.id}")
    print(f"Copyeditor User: {assignment.copyeditor.user.email}")
    print(f"\nAssigned By ID: {assignment.assigned_by.id}")
    print(f"Assigned By User: {assignment.assigned_by.user.email}")
    
    print(f"\nJournal: {assignment.submission.journal.title}")
    
    # Check all users
    print("\n" + "=" * 80)
    print("ALL USERS IN SYSTEM")
    print("=" * 80)
    for user in User.objects.all():
        has_profile = hasattr(user, 'profile')
        profile_id = user.profile.id if has_profile else None
        print(f"\nUser: {user.email}")
        print(f"  - ID: {user.id}")
        print(f"  - Has Profile: {has_profile}")
        print(f"  - Profile ID: {profile_id}")
        print(f"  - Is Superuser: {user.is_superuser}")
        print(f"  - Is Staff: {user.is_staff}")
        
        if has_profile:
            # Check if this user is the copyeditor
            if user.profile.id == assignment.copyeditor.id:
                print(f"  ✓ IS THE COPYEDITOR")
            
            # Check if this user is the assigner
            if user.profile.id == assignment.assigned_by.id:
                print(f"  ✓ IS THE ASSIGNER (assigned_by)")
            
            # Check journal staff
            from apps.journals.models import JournalStaff
            is_journal_staff = JournalStaff.objects.filter(
                journal=assignment.submission.journal,
                profile=user.profile,
                is_active=True
            ).exists()
            if is_journal_staff:
                print(f"  ✓ IS JOURNAL STAFF for {assignment.submission.journal.title}")
    
    print("\n" + "=" * 80)
    print("PERMISSION CHECK LOGIC")
    print("=" * 80)
    print("To start this assignment, user must be ONE of:")
    print("  1. Superuser or Staff")
    print("  2. Active Journal Staff for this journal")
    print(f"  3. The assigned copyeditor (Profile ID: {assignment.copyeditor.id})")
    print(f"  4. The assigner (Profile ID: {assignment.assigned_by.id})")
    
except CopyeditingAssignment.DoesNotExist:
    print(f"Assignment {assignment_id} not found")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
