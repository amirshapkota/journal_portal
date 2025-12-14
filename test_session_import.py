"""Test OJS import with session-based requests to bypass bot detection"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from apps.journals.models import Journal
from apps.integrations.ojs_sync import OJSSyncService

# Get the journal
journal_id = 'a01b9c60-fb12-4d51-8cc9-86db55859f6a'
journal = Journal.objects.get(id=journal_id)

print(f"Testing import for: {journal.title}")
print(f"OJS URL: {journal.ojs_api_url}")

# Create sync service (this will initialize the session)
sync_service = OJSSyncService(journal)
print(f"Session initialized with {len(sync_service.session.cookies)} cookies")

# Try importing (just first 1 submission for testing)
try:
    result = sync_service.import_from_ojs(max_items=1)
    print(f"\n✓ Import completed!")
    print(f"Results: {result}")
except Exception as e:
    print(f"\n✗ Import failed: {str(e)}")
    import traceback
    traceback.print_exc()
