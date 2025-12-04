"""
Test script to debug OJS submission creation and file upload.
This will help us understand the exact requirements of the OJS API.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

import requests
import json
from apps.journals.models import Journal
from apps.submissions.models import Submission
from apps.integrations.ojs_sync import OJSSyncService

def test_ojs_api():
    """Test OJS API step by step."""
    
    # Get the journal
    journal_id = '5c3bd875-a35d-4f3c-a026-122dab66ddcf'
    try:
        journal = Journal.objects.get(id=journal_id)
        print(f"✓ Found journal: {journal.title}")
        print(f"  OJS URL: {journal.ojs_api_url}")
        print(f"  OJS Journal ID: {journal.ojs_journal_id}")
    except Journal.DoesNotExist:
        print(f"✗ Journal {journal_id} not found")
        return
    
    if not journal.ojs_api_url or not journal.ojs_api_key:
        print("✗ OJS not configured for this journal")
        return
    
    api_url = journal.ojs_api_url
    api_key = journal.ojs_api_key
    context_id = journal.ojs_journal_id
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    print("\n" + "="*80)
    print("STEP 1: Fetch available genres (file types)")
    print("="*80)
    
    try:
        # Get genres from context
        genres_url = f"{api_url}/contexts/{context_id}"
        print(f"GET {genres_url}")
        response = requests.get(genres_url, headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            context_data = response.json()
            # Try to find genres in the response
            print(f"Context data keys: {context_data.keys()}")
            
            # Genres might be at a different endpoint
            genres_url = f"{api_url}/_submissions"
            print(f"\nTrying: GET {genres_url}")
            response = requests.get(genres_url, headers=headers, params={'contextId': context_id, 'count': 1})
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    # Look at an existing submission to see file structure
                    existing = data['items'][0]
                    print(f"Found existing submission ID: {existing.get('id')}")
                    
                    # Get its files
                    sub_id = existing.get('id')
                    files_url = f"{api_url}/submissions/{sub_id}/files"
                    print(f"\nGET {files_url}")
                    files_response = requests.get(files_url, headers=headers)
                    print(f"Status: {files_response.status_code}")
                    if files_response.status_code == 200:
                        files_data = files_response.json()
                        items = files_data.get('items', [])
                        if items:
                            print(f"Found {len(items)} files")
                            first_file = items[0]
                            print(f"File structure: {json.dumps(first_file, indent=2)}")
                            print(f"\nGenre ID: {first_file.get('genreId')}")
                            print(f"File Stage: {first_file.get('fileStage')}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*80)
    print("STEP 2: Find a test submission from Django")
    print("="*80)
    
    # Find a submission with files
    test_submission = Submission.objects.filter(
        journal=journal,
        documents__isnull=False
    ).first()
    
    if not test_submission:
        print("✗ No submissions with documents found")
        return
    
    print(f"✓ Found test submission: {test_submission.id}")
    print(f"  Title: {test_submission.title}")
    print(f"  Documents: {test_submission.documents.count()}")
    
    # Get first document with file
    document = test_submission.documents.filter(original_file__isnull=False).first()
    if not document:
        print("✗ No document with file found")
        return
    
    print(f"✓ Found document: {document.title}")
    print(f"  File: {document.original_file.name}")
    print(f"  Size: {document.file_size} bytes")
    
    print("\n" + "="*80)
    print("STEP 3: Create minimal submission in OJS")
    print("="*80)
    
    submission_data = {
        'contextId': int(context_id),
        'submissionProgress': 0,
    }
    
    url = f"{api_url}/submissions"
    print(f"POST {url}")
    print(f"Data: {json.dumps(submission_data, indent=2)}")
    
    response = requests.post(url, json=submission_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code not in [200, 201]:
        print("✗ Failed to create submission")
        return
    
    ojs_submission = response.json()
    ojs_id = ojs_submission.get('id')
    print(f"✓ Created OJS submission ID: {ojs_id}")
    
    print("\n" + "="*80)
    print("STEP 4: Create publication")
    print("="*80)
    
    # Get author info
    first_author = test_submission.author_contributions.order_by('order').first()
    if first_author:
        author_data = {
            'givenName': {'en_US': first_author.profile.user.first_name or 'Test'},
            'familyName': {'en_US': first_author.profile.user.last_name or 'Author'},
            'email': first_author.profile.user.email,
            'userGroupId': 14,
            'includeInBrowse': True,
            'primaryContact': True,
        }
    else:
        author_data = {
            'givenName': {'en_US': 'Test'},
            'familyName': {'en_US': 'Author'},
            'email': 'test@example.com',
            'userGroupId': 14,
            'includeInBrowse': True,
            'primaryContact': True,
        }
    
    publication_data = {
        'title': {'en_US': test_submission.title},
        'abstract': {'en_US': test_submission.abstract or 'Test abstract'},
        'locale': 'en_US',
        'authors': [author_data],
        'status': 1,
        'version': 1,  # Required field!
    }
    
    pub_url = f"{api_url}/submissions/{ojs_id}/publications"
    print(f"POST {pub_url}")
    print(f"Data: {json.dumps(publication_data, indent=2)}")
    
    response = requests.post(pub_url, json=publication_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code in [200, 201]:
        print("✓ Publication created successfully")
    else:
        print("✗ Failed to create publication")
    
    print("\n" + "="*80)
    print("STEP 5: Try different file upload approaches")
    print("="*80)
    
    # Read the file
    document.original_file.seek(0)
    file_content = document.original_file.read()
    file_name = document.file_name or document.original_file.name
    
    print(f"File to upload: {file_name}")
    print(f"File size: {len(file_content)} bytes")
    
    # Approach 1: Basic upload with genreId
    print("\n--- Approach 1: fileStage=2, genreId=1 ---")
    files = {'uploadedFile': (file_name, file_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
    form_data = {'fileStage': '2', 'genreId': '1'}
    
    upload_url = f"{api_url}/submissions/{ojs_id}/files"
    print(f"POST {upload_url}")
    print(f"Form data: {form_data}")
    
    response = requests.post(upload_url, headers={'Authorization': f'Bearer {api_key}'}, files=files, data=form_data, timeout=60)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code in [200, 201]:
        print("✓ Approach 1 SUCCESS!")
        return
    
    # Approach 2: Try different genreIds
    for genre_id in [1, 2, 3, 4, 5]:
        print(f"\n--- Approach 2: Trying genreId={genre_id} ---")
        document.original_file.seek(0)
        file_content = document.original_file.read()
        files = {'uploadedFile': (file_name, file_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
        form_data = {'fileStage': '2', 'genreId': str(genre_id)}
        
        response = requests.post(upload_url, headers={'Authorization': f'Bearer {api_key}'}, files=files, data=form_data, timeout=60)
        print(f"genreId={genre_id}: Status {response.status_code}")
        
        if response.status_code in [200, 201]:
            print(f"✓ SUCCESS with genreId={genre_id}!")
            print(f"Response: {response.text}")
            return
    
    # Approach 3: Check existing submissions for file upload patterns
    print("\n--- Approach 3: Analyze existing file in OJS ---")
    try:
        # Get a submission that has files
        subs_response = requests.get(f"{api_url}/_submissions", headers=headers, params={'contextId': context_id, 'count': 10})
        if subs_response.status_code == 200:
            subs = subs_response.json().get('items', [])
            for sub in subs:
                files_resp = requests.get(f"{api_url}/submissions/{sub['id']}/files", headers=headers)
                if files_resp.status_code == 200:
                    files = files_resp.json().get('items', [])
                    if files:
                        print(f"Found submission {sub['id']} with {len(files)} files")
                        for f in files[:1]:  # Just first file
                            print(f"File details:")
                            print(f"  genreId: {f.get('genreId')}")
                            print(f"  fileStage: {f.get('fileStage')}")
                            print(f"  uploaderUserId: {f.get('uploaderUserId')}")
                            print(f"  reviewRoundId: {f.get('reviewRoundId')}")
                            print(f"  assocType: {f.get('assocType')}")
                            print(f"  assocId: {f.get('assocId')}")
                            
                            # Try uploading with these exact parameters
                            print(f"\n--- Trying with discovered parameters ---")
                            document.original_file.seek(0)
                            file_content = document.original_file.read()
                            files_upload = {'uploadedFile': (file_name, file_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
                            form_data_discovered = {
                                'fileStage': str(f.get('fileStage')),
                                'genreId': str(f.get('genreId')),
                            }
                            
                            response = requests.post(upload_url, headers={'Authorization': f'Bearer {api_key}'}, files=files_upload, data=form_data_discovered, timeout=60)
                            print(f"Status: {response.status_code}")
                            print(f"Response: {response.text[:500]}")
                            
                            if response.status_code in [200, 201]:
                                print(f"✓ SUCCESS!")
                                return
                        break
    except Exception as e:
        print(f"Error: {e}")
    
    # Approach 4: Try using PHP session to upload
    print("\n--- Approach 4: Manual file upload may be required ---")
    print("OJS may require files to be uploaded through the web interface")
    
    # Approach 3: Check if we need to use a different endpoint
    print("\n--- Approach 3: Direct file wizard endpoint ---")
    # Some OJS installations might need the submission wizard endpoint
    wizard_url = f"{api_url.replace('/api/v1', '')}/submission/wizard/uploadSubmissionFile"
    print(f"Trying: {wizard_url}")
    print("(This approach may not work via REST API)")
    
    print("\n" + "="*80)
    print("INVESTIGATION COMPLETE")
    print("="*80)
    print(f"OJS Submission ID: {ojs_id}")
    print(f"Check the submission in OJS dashboard to see if it's visible")
    print(f"File upload failed - may need manual configuration or different approach")


if __name__ == '__main__':
    test_ojs_api()
