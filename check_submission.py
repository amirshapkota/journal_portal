#!/usr/bin/env python
"""Check a recently imported submission."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from apps.submissions.models import Submission

# Find the submission
s = Submission.objects.filter(title__icontains='MOVING AHEAD').first()

if s:
    print(f"\n{'='*60}")
    print(f"Title: {s.title}")
    print(f"Status: {s.status}")
    print(f"Authors: {s.author_contributions.count()}")
    print(f"Documents: {s.documents.count()}")
    
    # Check first author
    ac = s.author_contributions.first()
    if ac:
        print(f"\nFirst Author:")
        print(f"  Profile: {ac.profile}")
        print(f"  Display name: '{ac.profile.display_name}'")
        print(f"  User first name: '{ac.profile.user.first_name}'")
        print(f"  User last name: '{ac.profile.user.last_name}'")
        print(f"  Email: {ac.profile.user.email}")
    
    print(f"\nCorresponding Author: {s.corresponding_author}")
    if s.corresponding_author:
        print(f"  Display name: '{s.corresponding_author.display_name}'")
        print(f"  get_full_name(): {s.corresponding_author.get_full_name()}")
    
    print(f"{'='*60}\n")
else:
    print("\nSubmission not found yet. Import might still be running.")
