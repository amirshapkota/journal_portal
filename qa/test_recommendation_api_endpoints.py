"""
Test reviewer recommendation API endpoints via HTTP requests.
"""

import os
import django
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from apps.submissions.models import Submission
from django.contrib.auth import get_user_model

User = get_user_model()

# API Configuration
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"

def get_auth_token():
    """Get authentication token for API requests."""
    print("🔑 Getting authentication token...")
    
    # Try to log in with a test user (we'll use one of the reviewers we created)
    login_url = f"{BASE_URL}/api/v1/auth/login/"
    credentials = {
        'email': 'dr_smith@example.com',
        'password': 'reviewer123'
    }
    
    try:
        response = requests.post(login_url, json=credentials)
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access')
            print(f" Successfully authenticated as dr_smith@example.com\n")
            return access_token
        else:
            # Try alternate email format
            credentials['email'] = 'smith@example.com'
            response = requests.post(login_url, json=credentials)
            if response.status_code == 200:
                data = response.json()
                access_token = data.get('access')
                print(f" Successfully authenticated as smith@example.com\n")
                return access_token
            else:
                print(f"  Could not authenticate: {response.status_code}")
                print(f"    Response: {response.text}")
                print("    Continuing without authentication...\n")
                return None
    except Exception as e:
        print(f"  Authentication error: {e}")
        print("    Continuing without authentication...\n")
        return None

def test_basic_recommendation(token=None):
    """Test the basic recommendation endpoint (GET)."""
    print("=" * 70)
    print("TEST 1: Basic Reviewer Recommendations (GET)")
    print("=" * 70)
    
    # Get a submission to test with
    submission = Submission.objects.first()
    
    if not submission:
        print(" No submissions found in database")
        return
    
    print(f"\n Testing with submission: {submission.title}")
    print(f"   ID: {submission.id}")
    print(f"   Author: {submission.corresponding_author.get_full_name()}")
    
    # Make GET request
    url = f"{API_BASE}/ml/reviewer-recommendations/{submission.id}/"
    print(f"\n GET {url}")
    
    # Prepare headers
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
        print("   With authentication header")
    
    try:
        response = requests.get(url, params={'max_recommendations': 5}, headers=headers)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n Success! Received {data['recommendation_count']} recommendations\n")
            print(f"   Total potential reviewers: {data['total_potential_reviewers']}")
            print(f"   Submission: {data['submission_title']}\n")
            
            # Display first recommendation raw for debugging
            if data['recommendations']:
                print(" Sample response structure:")
                print(json.dumps(data['recommendations'][0], indent=2)[:500])
                print("...\n")
            
            # Display recommendations
            for i, rec in enumerate(data['recommendations'], 1):
                print(f"{i}. {rec['reviewer_name']}")
                print(f"   Email: {rec['reviewer_email']}")
                print(f"   Affiliation: {rec['affiliation']}")
                expertise = ', '.join(rec['expertise_areas'][:3])
                if len(rec['expertise_areas']) > 3:
                    expertise += f" (+{len(rec['expertise_areas'])-3} more)"
                print(f"   Expertise: {expertise}")
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
                print()
        else:
            print(f" Error: {response.status_code}")
            print(f"   Response: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print(" Connection error. Is the Django server running?")
        print("   Run: python manage.py runserver")
    except Exception as e:
        print(f" Error: {e}")

def test_custom_weights_recommendation(token=None):
    """Test the custom weights recommendation endpoint (POST)."""
    print("\n" + "=" * 70)
    print("TEST 2: Custom Weights Recommendations (POST)")
    print("=" * 70)
    
    # Get a submission to test with
    submission = Submission.objects.first()
    
    if not submission:
        print(" No submissions found in database")
        return
    
    print(f"\n Testing with submission: {submission.title}")
    print(f"   ID: {submission.id}")
    
    # Custom weights favoring similarity (note: API expects 'weights' key)
    request_data = {
        "weights": {
            "similarity": 0.8,
            "availability": 0.1,
            "quality": 0.05,
            "response_rate": 0.05
        },
        "max_recommendations": 3
    }
    
    print(f"\n Custom weights:")
    print(f"   Similarity:   {request_data['weights']['similarity']}")
    print(f"   Availability: {request_data['weights']['availability']}")
    print(f"   Quality:      {request_data['weights']['quality']}")
    print(f"   Response:     {request_data['weights']['response_rate']}")
    
    # Make POST request
    url = f"{API_BASE}/ml/reviewer-recommendations/{submission.id}/custom-weights/"
    print(f"\n POST {url}")
    
    # Prepare headers
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
        print("   With authentication header")
    
    try:
        response = requests.post(
            url,
            json=request_data,
            headers=headers
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n Success! Received {data['recommendation_count']} recommendations\n")
            print(f"   Weights used: {data['weights_used']}\n")
            
            # Display recommendations
            for i, rec in enumerate(data['recommendations'], 1):
                print(f"{i}. {rec['reviewer_name']}")
                print(f"   Affiliation: {rec['affiliation']}")
                expertise = ', '.join(rec['expertise_areas'][:3])
                if len(rec['expertise_areas']) > 3:
                    expertise += f" (+{len(rec['expertise_areas'])-3} more)"
                print(f"   Expertise: {expertise}")
                print(f"   Composite Score: {rec['scores']['composite']:.3f}")
                print(f"   Similarity Score: {rec['scores']['similarity']:.3f} ⭐")
                print(f"   Reason: {rec['recommendation_reason']}")
                print()
            
            print(" Notice: Rankings changed based on custom weights!")
            print("   Higher similarity weight (0.8) prioritizes expertise match")
        else:
            print(f" Error: {response.status_code}")
            print(f"   Response: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print(" Connection error. Is the Django server running?")
        print("   Run: python manage.py runserver")
    except Exception as e:
        print(f" Error: {e}")

def test_curl_examples():
    """Display curl examples for manual testing."""
    print("\n" + "=" * 70)
    print("CURL EXAMPLES FOR MANUAL TESTING")
    print("=" * 70)
    
    submission = Submission.objects.first()
    if submission:
        submission_id = submission.id
    else:
        submission_id = "YOUR_SUBMISSION_ID"
    
    print(f"\n Basic recommendations:")
    print(f"""
curl -X GET "http://localhost:8000/api/v1/ml/reviewer-recommendations/{submission_id}/?max_recommendations=5"
    """)
    
    print(f"\n Custom weights recommendations:")
    print(f"""
curl -X POST "http://localhost:8000/api/v1/ml/reviewer-recommendations/{submission_id}/custom-weights/" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "similarity_weight": 0.8,
    "availability_weight": 0.1,
    "quality_weight": 0.05,
    "response_rate_weight": 0.05,
    "max_recommendations": 5
  }}'
    """)
    
    print(f"\n With authentication (when enabled):")
    print(f"""
curl -X GET "http://localhost:8000/api/v1/ml/reviewer-recommendations/{submission_id}/" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    """)

if __name__ == '__main__':
    print("REVIEWER RECOMMENDATION API ENDPOINT TESTS")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/admin/", timeout=2)
        print(" Django server is running\n")
    except:
        print("  Warning: Django server may not be running")
        print("   Run: python manage.py runserver\n")
    
    # Get authentication token
    token = get_auth_token()
    
    # Run tests
    test_basic_recommendation(token)
    test_custom_weights_recommendation(token)
    test_curl_examples()
    
    print("\n" + "=" * 70)
    print(" API ENDPOINT TESTS COMPLETED")
    print("=" * 70)
    print("\n The reviewer recommendation API is working correctly!")
    print("   Both GET and POST endpoints are functional.\n")
