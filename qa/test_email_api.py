"""
Test Email System API Endpoints

This script tests all email-related API endpoints:
- Email preferences management
- Email logs viewing
- Email statistics

Usage:
    python qa/test_email_api.py
"""

import os
import sys
import django
import requests
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

CustomUser = get_user_model()

# Configuration
API_BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_EMAIL = "tapyze@gmail.com"

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")

def print_test(number, name):
    """Print a test header"""
    print(f"\n📧 Test {number}: {name}")
    print("-" * 70)

def get_or_create_test_user():
    """Get or create a test user and return auth token"""
    print("🔐 Setting up test user...")
    
    user, created = CustomUser.objects.get_or_create(
        email=TEST_EMAIL,
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True,
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✅ Created new test user: {TEST_EMAIL}")
    else:
        print(f"✅ Using existing test user: {TEST_EMAIL}")
    
    # Get or create auth token (JWT)
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    print(f"✅ Auth token: {access_token[:20]}...")
    
    return user, access_token

def make_request(method, endpoint, token, data=None, params=None):
    """Make an API request with authentication"""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    
    print(f"   → {method} {url}")
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        elif method == 'PATCH':
            response = requests.patch(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return response
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        print("   Make sure Django server is running:")
        print("   python manage.py runserver")
        return None
    except Exception as e:
        print(f"❌ Error making request: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_email_preferences(token):
    """Test email notification preferences endpoints"""
    print_header("EMAIL NOTIFICATION PREFERENCES")
    
    # Test 1: Get current preferences
    print_test(1, "Get Email Preferences")
    response = make_request('GET', '/notifications/email-preferences/', token)
    
    if response and response.status_code == 200:
        data = response.json()
        print(f"✅ Retrieved preferences successfully")
        print(f"   Email notifications enabled: {data.get('email_notifications_enabled')}")
        print(f"   Verification submitted: {data.get('email_on_verification_submitted')}")
        print(f"   Verification approved: {data.get('email_on_verification_approved')}")
        print(f"   ORCID connected: {data.get('email_on_orcid_connected')}")
        print(f"   Total preferences: {len([k for k in data.keys() if k.startswith('email_')])}")
        return True
    else:
        status = response.status_code if response else 'N/A'
        print(f"❌ Failed to get preferences (Status: {status})")
        if response:
            print(f"   Response: {response.text}")
        return False

def test_update_preferences(token):
    """Test updating email preferences"""
    print_test(2, "Update Email Preferences")
    
    # First get the preferences to get the ID
    response = make_request('GET', '/notifications/email-preferences/', token)
    if not response or response.status_code != 200:
        print(f"❌ Failed to get preferences first")
        return False
    
    data = response.json()
    # Handle both list and single object responses
    if isinstance(data, list) and len(data) > 0:
        prefs_id = data[0]['id']
    elif isinstance(data, dict):
        prefs_id = data['id']
    else:
        print(f"❌ Could not get preference ID")
        return False
    
    # Update specific preferences
    update_data = {
        'email_on_verification_submitted': True,
        'email_on_verification_approved': True,
        'email_on_verification_rejected': True,
        'email_on_verification_info_requested': True,
        'email_on_orcid_connected': True,
        'email_notifications_enabled': True,
    }
    
    response = make_request('PATCH', f'/notifications/email-preferences/{prefs_id}/', 
                           token, data=update_data)
    
    if response and response.status_code == 200:
        data = response.json()
        print(f"✅ Updated preferences successfully")
        print(f"   Verification emails: Enabled")
        print(f"   ORCID emails: Enabled")
        print(f"   Master switch: {data.get('email_notifications_enabled')}")
        return True
    else:
        status = response.status_code if response else 'N/A'
        print(f"❌ Failed to update preferences (Status: {status})")
        if response:
            print(f"   Response: {response.text}")
        return False

def test_toggle_all_notifications(token, enable=True):
    """Test toggling all notifications on/off"""
    action = "Enable" if enable else "Disable"
    print_test(3, f"{action} All Notifications")
    
    # First get the preferences to get the ID
    response = make_request('GET', '/notifications/email-preferences/', token)
    if not response or response.status_code != 200:
        print(f"❌ Failed to get preferences first")
        return False
    
    data = response.json()
    if isinstance(data, list) and len(data) > 0:
        prefs_id = data[0]['id']
    elif isinstance(data, dict):
        prefs_id = data['id']
    else:
        print(f"❌ Could not get preference ID")
        return False
    
    response = make_request('POST', f'/notifications/email-preferences/{prefs_id}/toggle_all/', 
                           token, data={'enabled': enable})
    
    if response and response.status_code == 200:
        data = response.json()
        print(f"✅ {action}d all notifications successfully")
        print(f"   Message: {data.get('message')}")
        print(f"   Master switch: {data.get('email_notifications_enabled')}")
        return True
    else:
        status = response.status_code if response else 'N/A'
        print(f"❌ Failed to toggle notifications (Status: {status})")
        if response:
            print(f"   Response: {response.text}")
        return False

def test_email_logs(token):
    """Test email logs viewing"""
    print_header("EMAIL LOGS")
    
    print_test(4, "Get Email Logs")
    response = make_request('GET', '/notifications/email-logs/', token)
    
    if response and response.status_code == 200:
        data = response.json()
        
        # Handle both paginated and non-paginated responses
        if isinstance(data, dict) and 'results' in data:
            logs = data['results']
            total = data.get('count', len(logs))
        else:
            logs = data
            total = len(logs)
        
        print(f"✅ Retrieved {len(logs)} email logs (Total: {total})")
        
        if logs:
            print("\n📧 Recent emails:")
            for i, log in enumerate(logs[:5], 1):
                template = log.get('template_type', 'Direct Email')
                status = log.get('status', 'UNKNOWN')
                subject = log.get('subject', 'No subject')
                created = log.get('created_at', 'Unknown date')
                
                status_icon = {
                    'SENT': '✅',
                    'PENDING': '⏳',
                    'FAILED': '❌',
                    'DELIVERED': '📬',
                }.get(status, '❓')
                
                print(f"  {i}. {status_icon} {template} - {status}")
                print(f"     Subject: {subject}")
                print(f"     Created: {created[:19] if len(created) > 19 else created}")
        else:
            print("   No email logs found yet")
        
        return True
    else:
        status = response.status_code if response else 'N/A'
        print(f"❌ Failed to get email logs (Status: {status})")
        if response:
            print(f"   Response: {response.text}")
        return False

def test_email_logs_filter(token):
    """Test filtering email logs"""
    print_test(5, "Filter Email Logs by Status")
    
    # Filter by SENT status
    response = make_request('GET', '/notifications/email-logs/', token, 
                           params={'status': 'SENT'})
    
    if response and response.status_code == 200:
        data = response.json()
        
        if isinstance(data, dict) and 'results' in data:
            logs = data['results']
            total = data.get('count', len(logs))
        else:
            logs = data
            total = len(logs)
        
        print(f"✅ Found {total} sent emails")
        
        # Filter by template type
        response2 = make_request('GET', '/notifications/email-logs/', token,
                                params={'template_type': 'VERIFICATION_SUBMITTED'})
        
        if response2 and response2.status_code == 200:
            data2 = response2.json()
            if isinstance(data2, dict) and 'results' in data2:
                logs2 = data2['results']
                total2 = data2.get('count', len(logs2))
            else:
                logs2 = data2
                total2 = len(logs2)
            
            print(f"✅ Found {total2} verification submitted emails")
        
        return True
    else:
        status = response.status_code if response else 'N/A'
        print(f"❌ Failed to filter email logs (Status: {status})")
        if response:
            print(f"   Response: {response.text}")
        return False

def test_email_statistics(token):
    """Test email statistics endpoint"""
    print_header("EMAIL STATISTICS")
    
    print_test(6, "Get Email Statistics")
    response = make_request('GET', '/notifications/email-logs/stats/', token)
    
    if response and response.status_code == 200:
        data = response.json()
        print(f"✅ Retrieved email statistics")
        print(f"\n📊 Overall Statistics:")
        print(f"   Total Emails: {data.get('total', 0)}")
        print(f"   Sent: {data.get('sent', 0)}")
        print(f"   Pending: {data.get('pending', 0)}")
        print(f"   Failed: {data.get('failed', 0)}")
        
        success_rate = data.get('success_rate', 0)
        print(f"   Success Rate: {success_rate}%")
        
        # By template type
        by_template = data.get('by_template_type', {})
        if by_template:
            print(f"\n📧 By Template Type:")
            for template, count in by_template.items():
                print(f"   {template}: {count}")
        
        return True
    else:
        status = response.status_code if response else 'N/A'
        print(f"❌ Failed to get statistics (Status: {status})")
        if response:
            print(f"   Response: {response.text}")
        return False

def test_user_email_statistics(token):
    """Test user-specific email statistics"""
    print_test(7, "Get User Email Statistics")
    response = make_request('GET', '/notifications/email-logs/user_stats/', token)
    
    if response and response.status_code == 200:
        data = response.json()
        print(f"✅ Retrieved user email statistics")
        print(f"\n👤 Your Email Statistics:")
        print(f"   Total: {data.get('total', 0)}")
        print(f"   Sent: {data.get('sent', 0)}")
        print(f"   Pending: {data.get('pending', 0)}")
        print(f"   Failed: {data.get('failed', 0)}")
        
        # Recent emails
        recent = data.get('recent_emails', [])
        if recent:
            print(f"\n📧 Recent Emails ({len(recent)}):")
            for email in recent[:3]:
                print(f"   - {email.get('subject')} ({email.get('status')})")
        
        return True
    else:
        status = response.status_code if response else 'N/A'
        print(f"❌ Failed to get user statistics (Status: {status})")
        if response:
            print(f"   Response: {response.text}")
        return False

def main():
    """Main test runner"""
    print("=" * 70)
    print("  EMAIL SYSTEM API ENDPOINT TESTS")
    print("=" * 70)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 API Base: {API_BASE_URL}")
    print(f"📧 Test Email: {TEST_EMAIL}")
    
    # Setup
    user, token = get_or_create_test_user()
    
    # Track results
    results = []
    
    # Run tests
    try:
        # Email Preferences Tests
        results.append(("Get Email Preferences", test_email_preferences(token)))
        results.append(("Update Email Preferences", test_update_preferences(token)))
        results.append(("Toggle All Notifications", test_toggle_all_notifications(token, True)))
        
        # Email Logs Tests
        results.append(("Get Email Logs", test_email_logs(token)))
        results.append(("Filter Email Logs", test_email_logs_filter(token)))
        
        # Statistics Tests
        results.append(("Get Email Statistics", test_email_statistics(token)))
        results.append(("Get User Statistics", test_user_email_statistics(token)))
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Results: {passed}/{total} tests passed\n")
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print("\n" + "=" * 70)
    
    if passed == total:
        print("✅ ALL TESTS PASSED!")
        print("\n📋 Available API Endpoints:")
        print("   GET    /api/v1/notifications/email-preferences/")
        print("   PATCH  /api/v1/notifications/email-preferences/update_preferences/")
        print("   POST   /api/v1/notifications/email-preferences/toggle_all/")
        print("   GET    /api/v1/notifications/email-logs/")
        print("   GET    /api/v1/notifications/email-logs/stats/")
        print("   GET    /api/v1/notifications/email-logs/user_stats/")
        print("\n💡 Tip: Use these endpoints in your frontend application!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure Django server is running: python manage.py runserver")
        print("   2. Check that migrations are applied: python manage.py migrate")
        print("   3. Verify email templates exist: python manage.py create_email_templates")
    
    print("=" * 70)
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
