"""
Script to create sample reviewers for testing the reviewer recommendation system.
Run this to populate the database with reviewers who have expertise areas.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.users.models import Profile, Role
from apps.common.models import Concept

User = get_user_model()

# Sample reviewer data with various expertise areas
SAMPLE_REVIEWERS = [
    {
        'username': 'dr_smith',
        'email': 'smith@example.com',
        'first_name': 'John',
        'last_name': 'Smith',
        'bio': 'Professor of Computer Science specializing in artificial intelligence and machine learning.',
        'expertise': ['Machine Learning', 'Deep Learning', 'Neural Networks', 'Computer Vision', 'Artificial Intelligence'],
        'affiliation': 'MIT Computer Science Department',
        'orcid': '0000-0001-1234-5678',
    },
    {
        'username': 'dr_johnson',
        'email': 'johnson@example.com',
        'first_name': 'Emily',
        'last_name': 'Johnson',
        'bio': 'Associate Professor specializing in bioinformatics and computational biology.',
        'expertise': ['Bioinformatics', 'Computational Biology', 'Genomics', 'Protein Structure', 'Systems Biology'],
        'affiliation': 'Stanford University',
        'orcid': '0000-0002-2345-6789',
    },
    {
        'username': 'dr_chen',
        'email': 'chen@example.com',
        'first_name': 'Wei',
        'last_name': 'Chen',
        'bio': 'Senior researcher in natural language processing and text mining.',
        'expertise': ['Natural Language Processing', 'Text Mining', 'Information Extraction', 'Sentiment Analysis'],
        'affiliation': 'Carnegie Mellon University',
        'orcid': '0000-0003-3456-7890',
    },
    {
        'username': 'dr_williams',
        'email': 'williams@example.com',
        'first_name': 'Sarah',
        'last_name': 'Williams',
        'bio': 'Expert in data science, statistical analysis, and predictive modeling.',
        'expertise': ['Data Science', 'Statistics', 'Predictive Modeling', 'Data Mining', 'Big Data Analytics'],
        'affiliation': 'UC Berkeley',
        'orcid': '0000-0004-4567-8901',
    },
    {
        'username': 'dr_garcia',
        'email': 'garcia@example.com',
        'first_name': 'Maria',
        'last_name': 'Garcia',
        'bio': 'Professor of Cybersecurity and Network Security.',
        'expertise': ['Cybersecurity', 'Network Security', 'Cryptography', 'Information Security', 'Threat Analysis'],
        'affiliation': 'Georgia Tech',
        'orcid': '0000-0005-5678-9012',
    },
    {
        'username': 'dr_brown',
        'email': 'brown@example.com',
        'first_name': 'Michael',
        'last_name': 'Brown',
        'bio': 'Researcher in software engineering and distributed systems.',
        'expertise': ['Software Engineering', 'Distributed Systems', 'Cloud Computing', 'Microservices', 'DevOps'],
        'affiliation': 'University of Washington',
        'orcid': '0000-0006-6789-0123',
    },
    {
        'username': 'dr_lee',
        'email': 'lee@example.com',
        'first_name': 'David',
        'last_name': 'Lee',
        'bio': 'Specialist in computer vision and image processing.',
        'expertise': ['Computer Vision', 'Image Processing', 'Object Detection', 'Image Recognition', 'Deep Learning'],
        'affiliation': 'Cornell University',
        'orcid': '0000-0007-7890-1234',
    },
    {
        'username': 'dr_anderson',
        'email': 'anderson@example.com',
        'first_name': 'Jennifer',
        'last_name': 'Anderson',
        'bio': 'Expert in quantum computing and quantum algorithms.',
        'expertise': ['Quantum Computing', 'Quantum Algorithms', 'Quantum Information', 'Quantum Physics', 'Quantum Cryptography'],
        'affiliation': 'Caltech',
        'orcid': '0000-0008-8901-2345',
    },
    {
        'username': 'dr_martinez',
        'email': 'martinez@example.com',
        'first_name': 'Carlos',
        'last_name': 'Martinez',
        'bio': 'Researcher in robotics and autonomous systems.',
        'expertise': ['Robotics', 'Autonomous Systems', 'Control Systems', 'Path Planning', 'Robot Learning'],
        'affiliation': 'MIT',
        'orcid': '0000-0009-9012-3456',
    },
    {
        'username': 'dr_taylor',
        'email': 'taylor@example.com',
        'first_name': 'Rachel',
        'last_name': 'Taylor',
        'bio': 'Professor specializing in human-computer interaction and UX design.',
        'expertise': ['Human-Computer Interaction', 'UX Design', 'User Research', 'Accessibility', 'Interface Design'],
        'affiliation': 'University of Michigan',
        'orcid': '0000-0010-0123-4567',
    },
]

def get_or_create_concept(name):
    """Get or create a concept by name."""
    # Try to find by name first
    try:
        concept = Concept.objects.get(name=name)
        return concept
    except Concept.DoesNotExist:
        # Create new concept with unique external_id
        import uuid
        concept = Concept.objects.create(
            name=name,
            provider='MANUAL',
            external_id=f'manual_{uuid.uuid4().hex[:8]}',
            description=f'Expertise area: {name}'
        )
        return concept


def create_reviewers():
    """Create sample reviewers with expertise areas."""
    
    print("\n" + "="*60)
    print("Creating Sample Reviewers")
    print("="*60 + "\n")
    
    # Get or create Reviewer role
    reviewer_role, role_created = Role.objects.get_or_create(
        name='REVIEWER',
        defaults={
            'description': 'Can review submissions and provide feedback'
        }
    )
    
    if role_created:
        print(f"✅ Created Reviewer role")
    else:
        print(f"ℹ️  Reviewer role already exists")
    
    created_count = 0
    updated_count = 0
    
    for reviewer_data in SAMPLE_REVIEWERS:
        username = reviewer_data['username']
        
        # Check if user already exists
        user, user_created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': reviewer_data['email'],
                'first_name': reviewer_data['first_name'],
                'last_name': reviewer_data['last_name'],
                'is_active': True,
            }
        )
        
        if user_created:
            user.set_password('reviewer123')  # Set a default password
            user.save()
            print(f"\n✅ Created user: {user.get_full_name()} ({username})")
            created_count += 1
        else:
            print(f"\nℹ️  User already exists: {user.get_full_name()} ({username})")
            updated_count += 1
        
        # Update or create profile
        profile, profile_created = Profile.objects.get_or_create(user=user)
        
        profile.bio = reviewer_data['bio']
        profile.affiliation_name = reviewer_data['affiliation']
        profile.orcid_id = reviewer_data.get('orcid', '')
        profile.display_name = f"{reviewer_data['first_name']} {reviewer_data['last_name']}"
        profile.save()
        
        # Add reviewer role
        if not profile.roles.filter(name='REVIEWER').exists():
            profile.roles.add(reviewer_role)
        
        # Add expertise areas as Concepts
        expertise_list = reviewer_data['expertise']
        concepts_added = []
        for expertise_name in expertise_list:
            concept = get_or_create_concept(expertise_name)
            if concept not in profile.expertise_areas.all():
                profile.expertise_areas.add(concept)
                concepts_added.append(expertise_name)
        
        action = "Created" if profile_created else "Updated"
        print(f"   {action} profile")
        print(f"   Affiliation: {reviewer_data['affiliation']}")
        print(f"   Expertise: {', '.join(expertise_list)}")
        if concepts_added:
            print(f"   Added {len(concepts_added)} new expertise concepts")
    
    print("\n" + "="*60)
    print(f"✅ Sample reviewers created successfully!")
    print(f"   New users: {created_count}")
    print(f"   Updated users: {updated_count}")
    print(f"   Total: {len(SAMPLE_REVIEWERS)}")
    print("="*60)
    print("\n💡 Now you can run: python test_reviewer_recommendations.py")
    print("   Default password for all reviewers: reviewer123\n")

if __name__ == '__main__':
    create_reviewers()
