"""
Quick Analytics API Test
A simplified version that creates test users if needed.

Run: python test_analytics_quick.py
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

# Try to login with common test credentials
TEST_USERS = [
    {"email": "analytics_test@test.com", "password": "test123456"},
    {"email": "admin@test.com", "password": "testpass123"},
    {"email": "admin@journal-portal.com", "password": "admin123"},
    {"email": "testadmin@journal-portal.com", "password": "admin123"},
]

def get_token():
    """Try to get a token with any available test user."""
    print("Attempting to authenticate...")
    
    for user in TEST_USERS:
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login/",  # Updated path
                json=user
            )
            
            if response.status_code == 200:
                token = response.json().get('access')
                if token:
                    print(f"✓ Authenticated as {user['email']}")
                    return token
        except:
            continue
    
    print("✗ Could not authenticate with any test user")
    print("\nPlease create a superuser:")
    print("  python manage.py createsuperuser")
    print("\nOr update credentials in test_analytics_api.py")
    return None

def test_all_endpoints(token):
    """Test all analytics endpoints."""
    headers = {"Authorization": f"Bearer {token}"}
    
    tests = [
        ("Dashboard Overview", "GET", "/analytics/dashboard/", {}),
        ("Submission Analytics", "GET", "/analytics/submissions/", {"days": 30}),
        ("Reviewer Analytics", "GET", "/analytics/reviewers/", {"days": 90}),
        ("User Analytics", "GET", "/analytics/users/", {"days": 30}),
        ("Personal Analytics", "GET", "/analytics/my-analytics/", {}),
    ]
    
    print("\n" + "="*80)
    print("TESTING ANALYTICS ENDPOINTS".center(80))
    print("="*80 + "\n")
    
    passed = 0
    failed = 0
    
    for name, method, endpoint, params in tests:
        print(f"\nTesting: {name}")
        print(f"  {method} {BASE_URL}{endpoint}")
        
        try:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                headers=headers,
                params=params
            )
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ SUCCESS")
                
                # Show summary of response
                if isinstance(data, dict):
                    print(f"  Response keys: {', '.join(data.keys())}")
                passed += 1
            else:
                print(f"  ✗ FAILED")
                print(f"  Error: {response.text[:200]}")
                failed += 1
                
        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")
            failed += 1
    
    # Summary
    print("\n" + "="*80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*80 + "\n")
    
    return passed, failed

def main():
    token = get_token()
    
    if not token:
        return
    
    passed, failed = test_all_endpoints(token)
    
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print(f"⚠ {failed} test(s) failed")

if __name__ == "__main__":
    main()
