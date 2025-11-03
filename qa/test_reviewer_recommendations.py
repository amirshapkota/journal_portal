"""
Test script for reviewer recommendation system.
Run this after installing scikit-learn and numpy.
"""
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from apps.ml.reviewer_recommendation import ReviewerRecommendationEngine
from apps.submissions.models import Submission
from apps.users.models import Profile
from apps.common.models import Concept


def test_reviewer_recommendations():
    """Test the reviewer recommendation system."""
    print("="*60)
    print("Testing Reviewer Recommendation System")
    print("="*60)
    
    # Check if scikit-learn is installed
    try:
        import sklearn
        import numpy as np
        print(f"\n scikit-learn version: {sklearn.__version__}")
        print(f" numpy version: {np.version.version}")
    except ImportError as e:
        print(f"\n Missing dependency: {e}")
        print("\nPlease install:")
        print("  pip install scikit-learn==1.5.2 numpy==2.0.2")
        return
    
    # Get a test submission
    submissions = Submission.objects.all()[:5]
    if not submissions:
        print("\n No submissions found. Create a test submission first.")
        return
    
    print(f"\n Found {submissions.count()} submissions to test")
    
    # Initialize engine
    engine = ReviewerRecommendationEngine()
    print(" Recommendation engine initialized")
    
    # Test with first submission
    submission = submissions[0]
    print(f"\n Testing with submission: {submission.title[:50]}...")
    print(f"   Abstract: {submission.abstract[:100] if submission.abstract else 'No abstract'}...")
    
    # Get potential reviewers
    potential_reviewers = engine.get_potential_reviewers(submission)
    print(f"\n👥 Found {len(potential_reviewers)} potential reviewers")
    
    if not potential_reviewers:
        print("\n  No potential reviewers found.")
        print("   Tips:")
        print("   1. Create users with Reviewer role")
        print("   2. Add expertise areas to reviewer profiles")
        print("   3. Ensure reviewers are not submission authors")
        return
    
    # Show sample reviewer info
    if potential_reviewers:
        reviewer = potential_reviewers[0]
        print(f"\n   Sample reviewer: {reviewer.display_name or reviewer.user.email}")
        expertise = list(reviewer.expertise_areas.values_list('name', flat=True))
        print(f"   Expertise: {expertise or 'No expertise areas'}")
    
    # Get recommendations
    print("\n🤖 Generating ML recommendations...")
    recommendations = engine.recommend_reviewers(
        submission=submission,
        max_recommendations=5
    )
    
    if not recommendations:
        print(" No recommendations generated")
        print("   Check that:")
        print("   - Submission has title/abstract/keywords")
        print("   - Reviewers have bio/expertise areas")
        return
    
    print(f"\n Generated {len(recommendations)} recommendations")
    print("\n" + "="*60)
    print("TOP RECOMMENDATIONS:")
    print("="*60)
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['reviewer_name']}")
        print(f"   Affiliation: {rec['affiliation'] or 'Not specified'}")
        print(f"   Expertise: {', '.join(rec['expertise_areas'][:3]) or 'None listed'}")
        print(f"   Scores:")
        print(f"     - Composite:    {rec['scores']['composite']:.3f}")
        print(f"     - Similarity:   {rec['scores']['similarity']:.3f}")
        print(f"     - Availability: {rec['scores']['availability']:.3f}")
        print(f"     - Quality:      {rec['scores']['quality']:.3f}")
        print(f"     - Response:     {rec['scores']['response_rate']:.3f}")
        print(f"   Metrics:")
        print(f"     - Active reviews: {rec['metrics']['active_reviews']}")
        print(f"     - Completed: {rec['metrics']['total_reviews_completed']}")
        print(f"   Reason: {rec['recommendation_reason']}")
    
    # Test custom weights
    print("\n" + "="*60)
    print("TESTING CUSTOM WEIGHTS:")
    print("="*60)
    print("Using weights: similarity=0.8, availability=0.1, quality=0.05, response_rate=0.05")
    
    custom_recommendations = engine.recommend_reviewers(
        submission=submission,
        max_recommendations=3,
        weights={
            'similarity': 0.8,
            'availability': 0.1,
            'quality': 0.05,
            'response_rate': 0.05
        }
    )
    
    for i, rec in enumerate(custom_recommendations, 1):
        print(f"\n{i}. {rec['reviewer_name']}")
        print(f"   Composite score: {rec['scores']['composite']:.3f}")
        print(f"   Similarity: {rec['scores']['similarity']:.3f}")
    
    print("\n" + "="*60)
    print(" ALL TESTS PASSED!")
    print("="*60)
    print("\nAPI Endpoints available:")
    print("  GET  /api/v1/ml/reviewer-recommendations/<submission_id>/")
    print("  POST /api/v1/ml/reviewer-recommendations/<submission_id>/custom-weights/")
    print("\nExample request:")
    print("""
    curl -X GET 'http://localhost:8000/api/v1/ml/reviewer-recommendations/<submission_id>/?max_recommendations=10' \\
      -H 'Authorization: Bearer YOUR_TOKEN'
    """)


if __name__ == "__main__":
    test_reviewer_recommendations()
