#!/usr/bin/env python
"""Test OJS data extraction and file download."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

import requests
from apps.journals.models import Journal

# Get journal
journal_id = 'a01b9c60-fb12-4d51-8cc9-86db55859f6a'
j = Journal.objects.get(id=journal_id)

print(f"\n{'='*60}")
print(f"Testing OJS Data Extraction for: {j.title}")
print(f"{'='*60}\n")

# Test submission data
submission_id = 1784
api_url = j.ojs_api_url
api_key = j.ojs_api_key

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("1. Fetching submission data...")
resp = requests.get(f"{api_url}/submissions/{submission_id}", headers=headers)
print(f"   Status: {resp.status_code}")

if resp.status_code == 200:
    data = resp.json()
    print(f"\n   Submission fields available:")
    for key in sorted(data.keys()):
        print(f"     - {key}: {type(data[key]).__name__}")
    
    # Check publications
    publications = data.get('publications', [])
    if publications:
        pub = publications[0]
        print(f"\n   Publication fields available:")
        for key in sorted(pub.keys()):
            value = pub[key]
            if isinstance(value, dict):
                print(f"     - {key}: dict with keys {list(value.keys())[:5]}")
            elif isinstance(value, list):
                print(f"     - {key}: list with {len(value)} items")
            else:
                print(f"     - {key}: {type(value).__name__} = {str(value)[:50]}")
        
        # Print specific metadata
        print(f"\n   Metadata extraction test:")
        print(f"     Section ID: {pub.get('sectionId')}")
        print(f"     Category IDs: {pub.get('categoryIds')}")
        print(f"     Keywords: {pub.get('keywords')}")
        print(f"     Disciplines: {pub.get('disciplines')}")
        print(f"     Subjects: {pub.get('subjects')}")
        print(f"     Coverage: {pub.get('coverage')}")
        print(f"     Languages: {pub.get('languages')}")
        print(f"     Pages: {pub.get('pages')}")
        print(f"     Copyright Year: {pub.get('copyrightYear')}")
        print(f"     Date Published: {pub.get('datePublished')}")

print("\n2. Testing file download methods...")

# Test file download
file_id = 12403
stage_id = 4
base_url = api_url.replace('/api/v1', '')

# Method 1: With Authorization header
print(f"\n   Method 1: With Authorization header")
file_api_url = f"{base_url}/$$$call$$$/api/file/file-api/download-file"
file_api_params = {
    'submissionFileId': file_id,
    'submissionId': submission_id,
    'stageId': stage_id
}
resp = requests.get(file_api_url, params=file_api_params, headers=headers)
print(f"     Status: {resp.status_code}")
print(f"     Content-Type: {resp.headers.get('Content-Type')}")
print(f"     Content-Length: {len(resp.content)} bytes")
if resp.status_code == 200:
    if 'application/json' in resp.headers.get('Content-Type', ''):
        print(f"     JSON Response: {resp.text}")
    else:
        print(f"     File downloaded successfully")
else:
    print(f"     Error: {resp.text[:200]}")

# Method 2: Without Authorization header
print(f"\n   Method 2: Without Authorization header")
simple_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
resp = requests.get(file_api_url, params=file_api_params, headers=simple_headers)
print(f"     Status: {resp.status_code}")
if resp.status_code == 200:
    print(f"     Content-Type: {resp.headers.get('Content-Type')}")
    print(f"     Content-Length: {len(resp.content)} bytes")
else:
    print(f"     Error: {resp.text[:200]}")

# Method 3: As browser (with cookies/session)
print(f"\n   Method 3: With session cookies")
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
})
resp = session.get(file_api_url, params=file_api_params)
print(f"     Status: {resp.status_code}")
if resp.status_code == 200:
    print(f"     Content-Type: {resp.headers.get('Content-Type')}")
    print(f"     Content-Length: {len(resp.content)} bytes")
else:
    print(f"     Error: {resp.text[:200]}")

print(f"\n{'='*60}\n")

# Method 4: Try getting galley download URL
print("3. Testing galley download...")
resp = requests.get(f"{api_url}/submissions/{submission_id}", headers=headers)
if resp.status_code == 200:
    data = resp.json()
    publications = data.get('publications', [])
    if publications:
        pub = publications[0]
        galleys = pub.get('galleys', [])
        print(f"   Found {len(galleys)} galley(s)")
        
        for galley in galleys:
            galley_id = galley.get('id')
            file_id = galley.get('submissionFileId')
            label = galley.get('label', {})
            
            print(f"\n   Galley ID: {galley_id}, File ID: {file_id}, Label: {label}")
            
            # Try public download URL
            download_url = f"{base_url}/article/download/{submission_id}/{galley_id}"
            print(f"   Trying: {download_url}")
            
            resp = requests.get(download_url, allow_redirects=True)
            print(f"   Status: {resp.status_code}")
            print(f"   Content-Type: {resp.headers.get('Content-Type')}")
            print(f"   Content-Length: {len(resp.content)} bytes")
            
            if resp.status_code == 200 and 'application/pdf' in resp.headers.get('Content-Type', ''):
                print(f"   ✓ SUCCESS! File downloaded")
            else:
                print(f"   Response preview: {resp.text[:200]}")

print(f"\n{'='*60}\n")
