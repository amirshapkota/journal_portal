"""
Final test: Create a complete submission in OJS with publication
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

def test_final_sync():
    # Get journal
    journal_id = '5c3bd875-a35d-4f3c-a026-122dab66ddcf'
    journal = Journal.objects.get(id=journal_id)
    print(f"Testing with journal: {journal.title}")
    
    # Find a test submission
    submission = Submission.objects.filter(
        journal=journal,
        author_contributions__isnull=False
    ).first()
    
    if not submission:
        print("No submission found")
        return
    
    print(f"\nSubmission: {submission.title}")
    print(f"ID: {submission.id}")
    print(f"Authors: {submission.author_contributions.count()}")
    print(f"Documents: {submission.documents.count()}")
    
    # Check if already synced
    try:
        existing = submission.ojs_mapping
        print(f"\nAlready synced to OJS ID: {existing.ojs_submission_id}")
        print("Deleting existing mapping to test fresh sync...")
        existing.delete()
    except:
        pass
    
    print("\n" + "="*80)
    print("SYNCING TO OJS")
    print("="*80)
    
    result = sync_submission_to_ojs(submission)
    
    print(f"\nResult: {result}")
    
    if result.get('success'):
        print(f"\n✓ SUCCESS!")
        print(f"  OJS ID: {result.get('ojs_id')}")
        print(f"  Action: {result.get('action')}")
        print(f"\nView in OJS:")
        print(f"  {journal.ojs_api_url.replace('/api/v1', '')}/workflow/access/{result.get('ojs_id')}")
    else:
        print(f"\n✗ FAILED")
        print(f"  Error: {result.get('error')}")

if __name__ == '__main__':
    test_final_sync()
