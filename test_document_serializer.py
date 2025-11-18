#!/usr/bin/env python
"""Test DocumentSerializer file_url field"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from apps.submissions.models import Document
from apps.submissions.serializers import DocumentSerializer
from django.test import RequestFactory

# Get a document with a file
doc = Document.objects.filter(original_file__isnull=False, original_file__gt='').first()

if not doc:
    print("No documents with files found")
    exit(1)

print(f"=== Testing DocumentSerializer ===")
print(f"Document: {doc.title}")
print(f"Has file: {bool(doc.original_file)}")
print(f"File path: {doc.original_file.name}")

# Create request context
rf = RequestFactory()
req = rf.get('/')
req.META['HTTP_HOST'] = 'localhost:8000'

# Serialize with context
serializer = DocumentSerializer(doc, context={'request': req})
data = serializer.data

print(f"\nSerializer output:")
print(f"  file_name: {data.get('file_name')}")
print(f"  file_size: {data.get('file_size')}")
print(f"  file_url: {data.get('file_url')}")

if data.get('file_url'):
    print("\n✅ DocumentSerializer now returns file_url!")
else:
    print("\n❌ file_url is still missing")
