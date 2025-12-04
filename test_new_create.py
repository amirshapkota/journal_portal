"""
Test creating a NEW submission (not update)
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from apps.journals.models import Journal
from apps.submissions.models import Submission
from apps.integrations.ojs_sync import sync_submission_to_ojs

def test_new_submission():
    # Get journal
    journal_id = '5c3bd875-a35d-4f3c-a026-122dab66ddcf'
    journal = Journal.objects.get(id=journal_id)
    
    # Find a submission that's NOT synced yet
    all_subs = Submission.objects.filter(journal=journal, author_contributions__isnull=False)
    
    for sub in all_subs:
        try:
            # Check if it has mapping
            mapping = sub.ojs_mapping
            # Has mapping, skip
            continue
        except:
            # No mapping found! This is a new one
            submission = sub
            break
    else:
        print("All submissions are already synced. Using first one and deleting mapping...")
        submission = all_subs.first()
        try:
            submission.ojs_mapping.delete()
        except:
            pass
    
    print(f"Testing NEW submission sync")
    print(f"Submission: {submission.title}")
    print(f"ID: {submission.id}")
    
    print("\n" + "="*80)
    print("CREATING IN OJS")
    print("="*80)
    
    result = sync_submission_to_ojs(submission)
    
    print(f"\nResult:")
    print(f"  Success: {result.get('success')}")
    print(f"  OJS ID: {result.get('ojs_id')}")
    print(f"  Action: {result.get('action')}")
    print(f"  Error: {result.get('error')}")
    
    if result.get('success'):
        ojs_id = result.get('ojs_id')
        print(f"\n✓ Submission created in OJS!")
        print(f"\nView in OJS Editorial Workflow:")
        print(f"  http://cheapradius.com/jpahs/index.php/jpahs/workflow/access/{ojs_id}")
        print(f"\nView in OJS Author Dashboard:")
        print(f"  http://cheapradius.com/jpahs/index.php/jpahs/authorDashboard/submission/{ojs_id}")
        
        # Check if visible
        print(f"\nThe submission should now be visible in the OJS dashboard.")
        print(f"Files may need to be uploaded manually through the OJS interface.")

if __name__ == '__main__':
    test_new_submission()
