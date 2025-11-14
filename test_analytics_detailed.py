"""
Detailed Analytics API Test with Full Response Display
Shows complete JSON responses for each endpoint.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/api/v1"
TOKEN = None

def get_token():
    """Get authentication token."""
    global TOKEN
    response = requests.post(
        f"{BASE_URL}/auth/login/",
        json={"email": "analytics_test@test.com", "password": "test123456"}
    )
    if response.status_code == 200:
        TOKEN = response.json().get('access')
        print("✓ Authenticated successfully\n")
        return True
    print("✗ Authentication failed")
    return False

def test_endpoint(name, url, params=None):
    """Test endpoint and display full response."""
    print("=" * 80)
    print(f"{name}")
    print("=" * 80)
    print(f"URL: {url}")
    if params:
        print(f"Params: {json.dumps(params, indent=2)}")
    print()
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(url, headers=headers, params=params)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\nResponse:")
        print(json.dumps(data, indent=2, default=str))
        print()
        return True
    else:
        print(f"Error: {response.text[:500]}")
        return False

def main():
    print("\n" + "=" * 80)
    print("ANALYTICS API - DETAILED TEST WITH FULL RESPONSES")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if not get_token():
        return
    
    # Get a journal ID
    journal_id = None
    response = requests.get(
        f"{BASE_URL}/journals/",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    if response.status_code == 200:
        results = response.json().get('results', [])
        if results:
            journal_id = results[0]['id']
            print(f"Using journal ID: {journal_id}\n")
    
    tests = [
        ("1. DASHBOARD OVERVIEW", f"{BASE_URL}/analytics/dashboard/", None),
        ("2. SUBMISSION ANALYTICS (30 days)", f"{BASE_URL}/analytics/submissions/", {"days": 30}),
        ("3. SUBMISSION ANALYTICS (90 days)", f"{BASE_URL}/analytics/submissions/", {"days": 90}),
        ("4. REVIEWER ANALYTICS", f"{BASE_URL}/analytics/reviewers/", {"days": 90}),
        ("5. USER ANALYTICS", f"{BASE_URL}/analytics/users/", {"days": 30}),
        ("6. PERSONAL ANALYTICS", f"{BASE_URL}/analytics/my-analytics/", None),
    ]
    
    if journal_id:
        tests.append(("7. JOURNAL ANALYTICS", f"{BASE_URL}/analytics/journals/", {
            "journal_id": journal_id,
            "days": 90
        }))
    
    passed = 0
    failed = 0
    
    for name, url, params in tests:
        if test_endpoint(name, url, params):
            passed += 1
        else:
            failed += 1
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

if __name__ == "__main__":
    main()
