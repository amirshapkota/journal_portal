#!/usr/bin/env python
"""Test OJS file download"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from apps.journals.models import Journal
from apps.integrations.ojs_sync import OJSSyncService

# Get journal
journal = Journal.objects.get(id='40e5025f-1fed-401c-a33e-31ccf4b4895a')
print(f"\nJournal: {journal.title}")
print(f"OJS API: {journal.ojs_api_url}")

# Test with a specific submission that has files
service = OJSSyncService(journal)

# Try importing submission 365 which you mentioned has files
print("\n" + "="*80)
print("Testing file import for submission 365")
print("="*80 + "\n")

import requests
headers = {
    'Authorization': f'Bearer {journal.ojs_api_key}',
    'Content-Type': 'application/json'
}

# Get submission files
files_url = f"{journal.ojs_api_url}/submissions/365/files"
print(f"Fetching files from: {files_url}")
resp = requests.get(files_url, headers=headers)
print(f"Response status: {resp.status_code}")

if resp.status_code == 200:
    files_data = resp.json()
    print(f"\nResponse type: {type(files_data)}")
    print(f"Response keys: {files_data.keys() if isinstance(files_data, dict) else 'N/A'}")
    
    # OJS returns items in a dict
    items = files_data.get('items', files_data if isinstance(files_data, list) else [])
    print(f"Found {len(items)} files")
    
    for file_data in items[:2]:  # Test first 2 files
        file_id = file_data.get('id')
        file_name = file_data.get('name', {}).get('en_US', 'unknown')
        file_stage = file_data.get('fileStage', 1)
        
        print(f"\n--- File {file_id}: {file_name} ---")
        print(f"File data keys: {file_data.keys()}")
        print(f"Full file data: {file_data}")
        print(f"File stage: {file_stage}")
        print(f"File path: {file_data.get('path')}")
        
        # Try direct file access
        base_url = journal.ojs_api_url.replace('/api/v1', '')
        file_path = file_data.get('path')
        
        if file_path:
            # Remove '/index.php/jpahs' to get base domain
            direct_file_url = f"{base_url.rsplit('/', 2)[0]}/files/{file_path}"
            print(f"\n--- Trying direct file URL: {direct_file_url} ---")
            
            direct_resp = requests.get(direct_file_url, allow_redirects=True)
            print(f"Status: {direct_resp.status_code}")
            print(f"Content-Type: {direct_resp.headers.get('Content-Type')}")
            print(f"Content-Length: {direct_resp.headers.get('Content-Length')}")
            print(f"Actual size: {len(direct_resp.content)} bytes")
            
            if len(direct_resp.content) < 500:
                print(f"Content: {direct_resp.content[:200]}")
            else:
                print(f"First 50 bytes: {direct_resp.content[:50]}")
        
        print(f"\n--- Trying file API ---")
        
        # Try download
        base_url = journal.ojs_api_url.replace('/api/v1', '')
        file_api_url = f"{base_url}/$$$call$$$/api/file/file-api/download-file"
        
        params = {
            'submissionFileId': file_id,
            'submissionId': 365,
            'stageId': file_stage
        }
        
        full_url = f"{file_api_url}?submissionFileId={file_id}&submissionId=365&stageId={file_stage}"
        print(f"Download URL: {full_url}")
        
        # Try with auth header
        file_headers = {
            'Authorization': f'Bearer {journal.ojs_api_key}',
        }
        
        file_resp = requests.get(file_api_url, params=params, headers=file_headers, allow_redirects=True)
        
        print(f"Status: {file_resp.status_code}")
        print(f"Content-Type: {file_resp.headers.get('Content-Type')}")
        print(f"Content-Length: {file_resp.headers.get('Content-Length')}")
        print(f"Actual content size: {len(file_resp.content)} bytes")
        
        if len(file_resp.content) < 500:
            print(f"Content preview: {file_resp.content}")
        else:
            print(f"Content start: {file_resp.content[:100]}")
        
        # Try alternative: direct file access via submissions API
        print(f"\n--- Trying alternative download method ---")
        
        # Get full submission details
        sub_url = f"{journal.ojs_api_url}/submissions/{365}"
        sub_resp = requests.get(sub_url, headers=headers)
        
        if sub_resp.status_code == 200:
            sub_data = sub_resp.json()
            print(f"Got submission data")
            
            # Check for file URLs in submission data
            publications = sub_data.get('publications', [])
            if publications:
                pub = publications[0]
                print(f"Publication ID: {pub.get('id')}")
                print(f"Publication fullTitle: {pub.get('fullTitle')}")
                
                # Try to get publication files
                pub_files_url = f"{journal.ojs_api_url}/_publications/{pub.get('id')}"
                pub_resp = requests.get(pub_files_url, headers=headers)
                print(f"Publication files status: {pub_resp.status_code}")
                
                if pub_resp.status_code == 200:
                    pub_data = pub_resp.json()
                    print(f"Publication data keys: {pub_data.keys()}")
                    
                    # Check if there's a downloadURL or similar
                    if 'galleys' in pub_data:
                        for galley in pub_data['galleys']:
                            print(f"Galley: {galley}")
        
        print()

print("\n" + "="*80)
