"""
Detailed file upload test
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

import requests
from apps.journals.models import Journal
from apps.submissions.models import Submission

# Get journal
journal_id = '5c3bd875-a35d-4f3c-a026-122dab66ddcf'
journal = Journal.objects.get(id=journal_id)

api_url = journal.ojs_api_url
api_key = journal.ojs_api_key

# Get a submission with file
submission = Submission.objects.filter(
    journal=journal,
    documents__original_file__isnull=False
).first()

if not submission:
    print("No submission with files found")
    exit()

document = submission.documents.filter(original_file__isnull=False).first()

print(f"Submission: {submission.title}")
print(f"Document: {document.title}")
print(f"File: {document.original_file.name}")

# Get OJS ID
try:
    ojs_id = submission.ojs_mapping.ojs_submission_id
    print(f"OJS ID: {ojs_id}")
except:
    print("Not synced to OJS yet")
    exit()

# Read file
document.original_file.seek(0)
file_content = document.original_file.read()
file_name = document.file_name or document.original_file.name

print(f"\nFile size: {len(file_content)} bytes")
print(f"File name: {file_name}")

# Try upload with name[en_US] format
print("\n" + "="*80)
print("ATTEMPT 1: With name[en_US] field")
print("="*80)

url = f"{api_url}/submissions/{ojs_id}/files"
headers = {'Authorization': f'Bearer {api_key}'}
files = {'file': (file_name, file_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
form_data = {
    'fileStage': '2',
    'genreId': '1',
    'name[en_US]': file_name,
    'submissionId': str(ojs_id),
}

print(f"POST {url}")
print(f"Form data: {form_data}")

response = requests.post(url, headers=headers, files=files, data=form_data, timeout=60)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code in [200, 201]:
    print("\n✓ SUCCESS!")
    exit()

# Try without name field
print("\n" + "="*80)
print("ATTEMPT 2: Without name field")
print("="*80)

document.original_file.seek(0)
file_content = document.original_file.read()
files = {'file': (file_name, file_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
form_data = {
    'fileStage': '2',
    'genreId': '1',
    'submissionId': str(ojs_id),
}

response = requests.post(url, headers=headers, files=files, data=form_data, timeout=60)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code in [200, 201]:
    print("\n✓ SUCCESS!")
    exit()

# Try with uploaderUserId
print("\n" + "="*80)
print("ATTEMPT 3: With uploaderUserId")
print("="*80)

# Get user ID from journal
try:
    from apps.users.models import CustomUser
    user = CustomUser.objects.filter(email='amir@omwaytech.com').first()
    if user:
        print(f"Found user: {user.email}")
except:
    pass

document.original_file.seek(0)
file_content = document.original_file.read()
files = {'file': (file_name, file_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
form_data = {
    'fileStage': '2',
    'genreId': '1',
}

response = requests.post(url, headers=headers, files=files, data=form_data, timeout=60)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code in [200, 201]:
    print("\n✓ SUCCESS!")
else:
    print("\n✗ All attempts failed")
    print("File upload via OJS REST API may not be supported")
