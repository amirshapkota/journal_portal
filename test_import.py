#!/usr/bin/env python
"""Test OJS import with logging."""
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

# Get journal
journal_id = 'a01b9c60-fb12-4d51-8cc9-86db55859f6a'
j = Journal.objects.get(id=journal_id)

print(f"\n{'='*60}")
print(f"Starting OJS import for: {j.title}")
print(f"{'='*60}\n")

# Run import
service = OJSSyncService(j)
result = service.import_all_from_ojs()

# Print summary
print(f"\n{'='*60}")
print("Import Summary:")
print(f"{'='*60}")
print(f"Total OJS Submissions: {result['total_ojs_submissions']}")
print(f"Imported: {result['imported']}")
print(f"Updated: {result['updated']}")
print(f"Skipped: {result['skipped']}")
print(f"Errors: {result['errors']}")

if result['error_details']:
    print("\nError Details:")
    for error in result['error_details'][:5]:  # Show first 5 errors
        print(f"  - {error}")
print(f"{'='*60}\n")
