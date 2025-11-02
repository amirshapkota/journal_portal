"""
Test script for OJS API integration endpoints.
Tests all OJS sync endpoints to verify connectivity and functionality.
"""
import requests
import json
from getpass import getpass

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1/integrations/ojs"

def get_auth_token():
    """Get JWT token for authentication."""
    email = input("Enter your email: ")
    password = getpass("Enter your password: ")
    
    response = requests.post(
        "http://127.0.0.1:8000/api/v1/auth/login/",
        json={"email": email, "password": password}
    )
    
    if response.status_code == 200:
        token = response.json().get('access')
        print("✅ Authentication successful\n")
        return token
    else:
        print(f"❌ Authentication failed: {response.status_code}")
        print(response.text)
        return None

def test_endpoint(name, method, url, headers, data=None):
    """Test a single endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Method: {method} | URL: {url}")
    print(f"{'='*60}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code in [200, 201, 204]:
            print(f"✅ SUCCESS")
            if response.status_code != 204:
                try:
                    result = response.json()
                    print(f"Response: {json.dumps(result, indent=2)[:500]}...")
                except:
                    print(f"Response: {response.text[:500]}...")
        else:
            print(f"❌ FAILED")
            print(f"Response: {response.text[:500]}")
        
        return response
    
    except requests.exceptions.Timeout:
        print(f"⏱️  TIMEOUT - OJS server may be slow or unreachable")
        return None
    except requests.exceptions.ConnectionError:
        print(f"🔌 CONNECTION ERROR - Cannot reach OJS server")
        return None
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None

def main():
    """Run all OJS API tests."""
    print("\n" + "="*60)
    print("OJS API Integration Test Suite")
    print("="*60)
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: List Journals
    test_endpoint(
        "List OJS Journals",
        "GET",
        f"{BASE_URL}/journals/",
        headers
    )
    
    # Test 2: List Articles
    test_endpoint(
        "List OJS Articles",
        "GET",
        f"{BASE_URL}/articles/",
        headers
    )
    
    # Test 3: List Users
    test_endpoint(
        "List OJS Users",
        "GET",
        f"{BASE_URL}/users/",
        headers
    )
    
    # Test 4: List Reviews
    test_endpoint(
        "List OJS Reviews",
        "GET",
        f"{BASE_URL}/reviews/",
        headers
    )
    
    # Test 5: List Comments
    test_endpoint(
        "List OJS Comments",
        "GET",
        f"{BASE_URL}/comments/",
        headers
    )
    
    # Test 6: List Submissions
    test_endpoint(
        "List OJS Submissions",
        "GET",
        f"{BASE_URL}/submissions/",
        headers
    )
    
    print("\n" + "="*60)
    print("Test Suite Complete!")
    print("="*60)
    print("\nNOTE: If you see 502 Bad Gateway errors, this means:")
    print("1. The OJS API endpoint URL or API key is incorrect")
    print("2. The OJS server is not accessible from your network")
    print("3. The OJS REST API plugin is not enabled")
    print("\nCheck your .env file and OJS configuration.")

if __name__ == "__main__":
    main()
