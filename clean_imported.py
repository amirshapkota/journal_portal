#!/usr/bin/env python
"""Clean all imported OJS submissions."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from apps.submissions.models import Submission
from apps.integrations.models import OJSMapping
from apps.journals.models import Journal

journal_id = 'a01b9c60-fb12-4d51-8cc9-86db55859f6a'

# Get journal
journal = Journal.objects.get(id=journal_id)

print("\n" + "="*60)
print(f"Cleaning imported OJS submissions for: {journal.title}")
print("="*60 + "\n")

# Get all submissions for this journal
submissions = Submission.objects.filter(journal=journal)
submission_count = submissions.count()

# Get all OJS mappings for these submissions
mappings = OJSMapping.objects.filter(local_submission__in=submissions)
mapping_count = mappings.count()

print(f"Found {mapping_count} OJS mappings")
print(f"Found {submission_count} imported submissions")

if submission_count > 0:
    confirm = input(f"\nAre you sure you want to delete {submission_count} submissions? (yes/no): ")
    
    if confirm.lower() == 'yes':
        # Delete mappings first
        print(f"\nDeleting {mapping_count} OJS mappings...")
        mappings.delete()
        print(f"✓ Deleted {mapping_count} mappings")
        
        # Delete submissions
        print(f"\nDeleting {submission_count} submissions...")
        submissions.delete()
        print(f"✓ Deleted {submission_count} submissions")
        
        print("\n" + "="*60)
        print("Cleanup completed successfully!")
        print("="*60 + "\n")
    else:
        print("\nCancelled. No submissions were deleted.")
else:
    print("\nNo imported submissions found.")

print()
