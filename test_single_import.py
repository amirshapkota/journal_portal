#!/usr/bin/env python
"""Test importing a single OJS submission."""
import os
import sys
import django
import logging

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

from apps.journals.models import Journal
from apps.integrations.ojs_sync import OJSSyncService
from apps.submissions.models import Submission
from apps.integrations.models import OJSMapping

# Get journal
journal_id = 'a01b9c60-fb12-4d51-8cc9-86db55859f6a'
j = Journal.objects.get(id=journal_id)

print(f"\n{'='*60}")
print(f"Testing single submission import from: {j.title}")
print(f"{'='*60}\n")

# Test with submission 1784
test_ojs_id = 1784

# Delete if already imported
existing_mapping = OJSMapping.objects.filter(ojs_submission_id=str(test_ojs_id)).first()
if existing_mapping:
    print(f"Deleting existing submission: {existing_mapping.local_submission.title}")
    existing_mapping.local_submission.delete()
    existing_mapping.delete()

# Import single submission
service = OJSSyncService(j)

print(f"Importing OJS submission {test_ojs_id}...\n")

try:
    # Fetch the submission data
    from apps.integrations.utils import ojs_list_submissions
    import requests
    
    api_url = j.ojs_api_url
    api_key = j.ojs_api_key
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    resp = requests.get(f"{api_url}/submissions/{test_ojs_id}", headers=headers)
    ojs_submission = resp.json()
    
    # Import it
    result = service._import_single_submission(ojs_submission)
    
    print(f"\n{'='*60}")
    print(f"Import result: {result}")
    print(f"{'='*60}\n")
    
    # Check the imported submission
    submission = Submission.objects.filter(title__icontains='jcmc').order_by('-created_at').first()
    
    if submission:
        print(f"Imported Submission Details:")
        print(f"  ID: {submission.id}")
        print(f"  Title: {submission.title}")
        print(f"  Abstract: {submission.abstract[:100]}...")
        print(f"  Status: {submission.status}")
        print(f"  Submitted: {submission.submitted_at}")
        print(f"  Authors: {submission.author_contributions.count()}")
        
        # Check authors
        for ac in submission.author_contributions.all():
            print(f"    - {ac.profile.display_name or ac.profile.user.email} ({ac.contrib_role})")
        
        print(f"  Corresponding Author: {submission.corresponding_author}")
        print(f"  Documents: {submission.documents.count()}")
        
        # Check documents
        for doc in submission.documents.all():
            print(f"    - {doc.title} ({doc.file_size} bytes)")
        
        print(f"  Section: {submission.section}")
        print(f"  Category: {submission.category}")
        print(f"  Research Type: {submission.research_type}")
        print(f"  Area: {submission.area}")
        
        # Check mapping
        mapping = OJSMapping.objects.filter(local_submission=submission).first()
        if mapping:
            print(f"\n  OJS Mapping:")
            print(f"    OJS ID: {mapping.ojs_submission_id}")
            print(f"    Sync Status: {mapping.sync_status}")
            print(f"    Last Synced: {mapping.last_synced_at}")
    
except Exception as e:
    print(f"\nError during import: {str(e)}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*60}\n")
