"""
Test verification status endpoint with score breakdown.
"""
import os
import django
import requests
import json
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

# API Configuration
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"

def get_auth_token():
    """Get authentication token."""
    print("🔐 Getting authentication token...")
    
    credentials = {
        'email': 'smith@example.com',
        'password': 'reviewer123'
    }
    
    try:
        response = requests.post(f"{API_BASE}/auth/login/", json=credentials)
        if response.status_code == 200:
            data = response.json()
            token = data.get('access') or data.get('access_token')
            print(f"✅ Authenticated as smith@example.com\n")
            return token
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_verification_status(token):
    """Test verification status endpoint."""
    print("="*80)
    print("  📊 VERIFICATION STATUS WITH SCORE BREAKDOWN")
    print("="*80)
    
    if not token:
        print("❌ No authentication token available")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        print("\n🔍 Fetching verification status...")
        response = requests.get(
            f"{API_BASE}/users/verification/status/",
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            data = response.json()
            
            print("📋 VERIFICATION STATUS")
            print("-" * 80)
            print(f"Profile Status: {data.get('profile_status')}")
            print(f"Is Verified: {data.get('is_verified')}")
            print(f"Has Pending Request: {data.get('has_pending_request')}")
            print(f"ORCID Connected: {data.get('orcid_connected')}")
            print(f"Roles: {', '.join(data.get('roles', []))}")
            
            latest_request = data.get('latest_request')
            if latest_request:
                print("\n📝 LATEST VERIFICATION REQUEST")
                print("-" * 80)
                print(f"Status: {latest_request.get('status')}")
                print(f"Requested Role: {latest_request.get('requested_role')}")
                print(f"Created: {latest_request.get('created_at')}")
                print(f"\n🎯 AUTO-SCORE: {latest_request.get('auto_score')}/100")
                
                score_breakdown = latest_request.get('score_breakdown', [])
                if score_breakdown:
                    print("\n📊 SCORE BREAKDOWN (Individual Points)")
                    print("=" * 80)
                    
                    for item in score_breakdown:
                        criterion = item['criterion']
                        earned = item['points_earned']
                        possible = item['points_possible']
                        status = item['status']
                        description = item['description']
                        weight = item['weight']
                        
                        # Status emoji
                        status_emoji = "✅" if status == 'completed' else "❌"
                        
                        # Progress bar
                        progress = int((earned / possible) * 20) if possible > 0 else 0
                        bar = "█" * progress + "░" * (20 - progress)
                        
                        print(f"\n{status_emoji} {criterion}")
                        print(f"   {description}")
                        print(f"   Weight: {weight.upper()}")
                        print(f"   Points: {earned}/{possible}")
                        print(f"   [{bar}] {int((earned/possible)*100)}%")
                    
                    print("\n" + "=" * 80)
                    
                    # Calculate totals
                    total_earned = sum(item['points_earned'] for item in score_breakdown)
                    total_possible = sum(item['points_possible'] for item in score_breakdown)
                    
                    print(f"TOTAL: {total_earned}/{total_possible} points")
                    
                    # Recommendations
                    print("\n💡 RECOMMENDATIONS TO IMPROVE SCORE:")
                    print("-" * 80)
                    missing_items = [item for item in score_breakdown if item['status'] == 'missing']
                    if missing_items:
                        for item in missing_items:
                            print(f"• {item['criterion']} (+{item['points_possible']} points)")
                            print(f"  → {item['description']}")
                    else:
                        print("✨ All criteria completed! Maximum score achieved.")
                
            else:
                print("\n⚠️ No verification request found")
            
            print("\n" + "=" * 80)
            print("✅ Test completed successfully!")
            
            # Print JSON for reference
            print("\n📄 FULL JSON RESPONSE:")
            print("-" * 80)
            print(json.dumps(data, indent=2))
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run the test."""
    print("\n" + "="*80)
    print("  🧪 TESTING VERIFICATION STATUS ENDPOINT")
    print("="*80 + "\n")
    
    # Check if server is running
    try:
        response = requests.get(BASE_URL, timeout=2)
        print("✅ Server is running\n")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Django server not running!")
        print("   Please start the server: python manage.py runserver")
        return
    
    # Get authentication
    token = get_auth_token()
    
    if not token:
        print("\n⚠️ Could not authenticate. Make sure user exists:")
        print("   Email: smith@example.com")
        print("   Password: reviewer123")
        return
    
    # Test the endpoint
    test_verification_status(token)

if __name__ == "__main__":
    main()
