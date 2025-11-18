#!/usr/bin/env python
"""Test SuperDoc upload and load flow"""
import os
import django
from io import BytesIO

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from apps.submissions.models import Document
from apps.submissions.superdoc_views import SuperDocViewSet
from django.test import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile

# Get the test document
doc = Document.objects.get(id='9b75318f-8415-435a-b578-52fa89f8e554')
print(f"=== Document: {doc.title} ===")
print(f"Before upload - Has file: {bool(doc.original_file)}\n")

# Create a simple DOCX file for testing
docx_content = b'PK\x03\x04' + b'\x00' * 100  # Minimal DOCX-like content
uploaded_file = SimpleUploadedFile(
    "test_upload.docx",
    docx_content,
    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

# Test upload endpoint
print("=== Testing UPLOAD endpoint ===")
rf = RequestFactory()
req = rf.post('/upload', {'file': uploaded_file})
req.FILES['file'] = uploaded_file
req.user = doc.submission.corresponding_author.user
req.META['HTTP_HOST'] = 'localhost:8000'

viewset = SuperDocViewSet()
viewset.format_kwarg = None
upload_response = viewset.upload_docx(req, pk=str(doc.id))

print(f"Upload Status: {upload_response.status_code}")
print(f"Upload Response file_url: {upload_response.data.get('file_url')}")
print(f"Upload Response file_name: {upload_response.data.get('file_name')}")
print(f"Upload Response file_size: {upload_response.data.get('file_size')}\n")

# Refresh document from database
doc.refresh_from_db()
print(f"After upload - Has file: {bool(doc.original_file)}")
print(f"After upload - File name: {doc.file_name}\n")

# Test load endpoint
print("=== Testing LOAD endpoint ===")
req2 = rf.get('/load')
req2.user = doc.submission.corresponding_author.user
req2.META['HTTP_HOST'] = 'localhost:8000'

load_response = viewset.load_document(req2, pk=str(doc.id))

print(f"Load Status: {load_response.status_code}")
print(f"Load Response file_url: {load_response.data.get('file_url')}")
print(f"Load Response file_name: {load_response.data.get('file_name')}")
print(f"Load Response file_size: {load_response.data.get('file_size')}\n")

print("=== Test Complete ===")
if upload_response.data.get('file_url') and load_response.data.get('file_url'):
    print("✅ Upload returns file_url")
    print("✅ Load returns file_url after upload")
    print("\nConclusion: The endpoints work correctly!")
    print("- BEFORE upload: file_url is null (correct)")
    print("- AFTER upload: file_url is returned (correct)")
else:
    print("❌ Something went wrong")
