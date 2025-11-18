#!/usr/bin/env python
"""Fix existing document to link file from version"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from apps.submissions.models import Document, DocumentVersion

# Get the document
doc = Document.objects.get(id='a97f64b5-ab1c-454b-bb62-719503f9dd74')
print(f"Document: {doc.title}")
print(f"Before - Has file: {bool(doc.original_file)}")

# Get the version
version = doc.versions.first()
if version:
    print(f"\nVersion file: {version.file.name}")
    print(f"Version file_name: {version.file_name}")
    print(f"Version file_size: {version.file_size}")
    
    # Copy file info to document
    doc.original_file = version.file
    doc.file_name = version.file_name
    doc.file_size = version.file_size
    doc.save()
    
    print(f"\n✅ Fixed! Document now has file: {doc.original_file.name}")
else:
    print("\n❌ No version found")
