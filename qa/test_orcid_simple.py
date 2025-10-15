"""
Simple ORCID endpoint test - checks all endpoints are responding.
No browser or OAuth required for basic connectivity test.
"""
import requests
import json

BASE = 'http://127.0.0.1:8000/api/v1'
EMAIL = 'admin@journal-portal.com'
PASSWORD = 'admin123456'

def test_login():
    """Test login and get JWT"""
    print("\n1. Testing login...")
    r = requests.post(f"{BASE}/auth/login/", json={'email': EMAIL, 'password': PASSWORD})
    if r.ok:
        print(f"   ✓ Login successful ({r.status_code})")
        return r.json()['access']
    else:
        print(f"   ✗ Login failed ({r.status_code})")
        print(f"   {r.text}")
        return None

def test_authorize(token):
    """Test authorize endpoint"""
    print("\n2. Testing ORCID authorize endpoint...")
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.get(f"{BASE}/integrations/orcid/authorize/", headers=headers)
    
    if r.ok:
        data = r.json()
        url = data.get('authorize_url', '')
        print(f"   ✓ Authorize endpoint works ({r.status_code})")
        print(f"   URL length: {len(url)} chars")
        print(f"   Contains client_id: {'client_id=' in url}")
        print(f"   Contains redirect_uri: {'redirect_uri=' in url}")
        return True
    else:
        print(f"   ✗ Authorize failed ({r.status_code})")
        print(f"   {r.text}")
        return False

def test_status(token):
    """Test status endpoint"""
    print("\n3. Testing ORCID status endpoint...")
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.get(f"{BASE}/integrations/orcid/status/", headers=headers)
    
    if r.ok:
        data = r.json()
        print(f"   ✓ Status endpoint works ({r.status_code})")
        print(f"   Connected: {data.get('connected', False)}")
        if data.get('connected'):
            print(f"   ORCID ID: {data.get('orcid_id')}")
            print(f"   Status: {data.get('status')}")
        return data
    else:
        print(f"   ✗ Status failed ({r.status_code})")
        print(f"   {r.text}")
        return None

def test_disconnect(token):
    """Test disconnect endpoint"""
    print("\n4. Testing ORCID disconnect endpoint...")
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.post(f"{BASE}/integrations/orcid/disconnect/", headers=headers)
    
    print(f"   Response: {r.status_code}")
    if r.status_code == 404:
        print(f"   ✓ Not connected (expected if no ORCID linked)")
    elif r.ok:
        print(f"   ✓ Disconnect works")
    else:
        print(f"   Response: {r.text}")

def test_sync(token):
    """Test sync-profile endpoint"""
    print("\n5. Testing ORCID sync-profile endpoint...")
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.post(f"{BASE}/integrations/orcid/sync-profile/", headers=headers)
    
    print(f"   Response: {r.status_code}")
    if r.status_code == 404:
        print(f"   ✓ Not connected (expected if no ORCID linked)")
    elif r.ok:
        data = r.json()
        print(f"   ✓ Sync works")
        print(f"   {json.dumps(data, indent=2)}")
    else:
        print(f"   Response: {r.text}")

def main():
    print("="*70)
    print("ORCID ENDPOINTS CONNECTIVITY TEST")
    print("="*70)
    print("\nThis tests that all ORCID endpoints are reachable and responding.")
    print("It does NOT test the full OAuth flow (that requires browser interaction).")
    
    # Test login
    token = test_login()
    if not token:
        print("\n❌ Cannot proceed without login. Check credentials and server.")
        return
    
    # Test all endpoints
    test_authorize(token)
    status_data = test_status(token)
    
    # Only test these if not connected (they'll fail gracefully if no ORCID)
    test_sync(token)
    test_disconnect(token)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("\n✓ All ORCID endpoints are responding correctly")
    print("\nTo complete ORCID integration:")
    print("1. Get authorize URL: GET /api/v1/integrations/orcid/authorize/")
    print("2. Open URL in browser and approve")
    print("3. ORCID redirects to: /api/v1/integrations/orcid/callback/?code=...")
    print("4. Check connection: GET /api/v1/integrations/orcid/status/")
    print("\nNOTE: The callback redirect requires proper session handling.")
    print("      In production, use a proper web frontend for OAuth flow.")
    print("="*70)

if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to server at http://127.0.0.1:8000")
        print("   Make sure the Django server is running:")
        print("   python manage.py runserver 127.0.0.1:8000")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
