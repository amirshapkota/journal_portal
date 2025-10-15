"""
Simple Email API Test using Django REST Framework TestClient

Tests all email system API endpoints directly without HTTP server.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.notifications.models import EmailNotificationPreference, EmailLog, EmailTemplate

CustomUser = get_user_model()

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")

def print_test(number, name):
    """Print a test header"""
    print(f"\n📧 Test {number}: {name}")
    print("-" * 70)

def setup_test_user():
    """Setup test user and client"""
    print("🔐 Setting up test environment...")
    
    user, created = CustomUser.objects.get_or_create(
        email='tapyze@gmail.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True,
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✅ Created new test user: {user.email}")
    else:
        print(f"✅ Using existing test user: {user.email}")
    
    # Create email preferences if they don't exist
    prefs, created = EmailNotificationPreference.objects.get_or_create(
        user=user,
        defaults={'email_notifications_enabled': True}
    )
    print(f"✅ Email preferences: {'Created' if created else 'Exists'}")
    
    # Setup API client with JWT auth
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    print(f"✅ API client configured with JWT auth")
    
    return user, client

def test_email_preferences(client):
    """Test email notification preferences endpoints"""
    print_header("EMAIL NOTIFICATION PREFERENCES")
    results = []
    
    # Test 1: List preferences (GET)
    print_test(1, "Get Email Preferences")
    response = client.get('/api/v1/notifications/email-preferences/')
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            data = data[0]  # Get first result from list
        
        print(f"✅ Retrieved preferences successfully")
        print(f"   Email notifications: {data.get('email_notifications_enabled')}")
        print(f"   Verification submitted: {data.get('email_on_verification_submitted')}")
        print(f"   Verification approved: {data.get('email_on_verification_approved')}")
        print(f"   ORCID connected: {data.get('email_on_orcid_connected')}")
        results.append(("Get Preferences", True))
    else:
        print(f"❌ Failed: {response.data if hasattr(response, 'data') else response.content}")
        results.append(("Get Preferences", False))
    
    # Test 2: Update preferences (PATCH)
    print_test(2, "Update Email Preferences")
    update_data = {
        'email_on_verification_submitted': True,
        'email_on_verification_approved': True,
        'email_on_verification_rejected': True,
        'email_on_orcid_connected': True,
    }
    
    # Try updating the first object
    prefs = EmailNotificationPreference.objects.first()
    response = client.patch(f'/api/v1/notifications/email-preferences/{prefs.id}/', update_data, format='json')
    print(f"   Status: {response.status_code}")
    
    if response.status_code in [200, 201]:
        print(f"✅ Updated preferences successfully")
        print(f"   Verification emails: Enabled")
        print(f"   ORCID emails: Enabled")
        results.append(("Update Preferences", True))
    else:
        print(f"❌ Failed: {response.data if hasattr(response, 'data') else response.content}")
        results.append(("Update Preferences", False))
    
    # Test 3: Toggle all notifications
    print_test(3, "Toggle All Notifications")
    response = client.post(f'/api/v1/notifications/email-preferences/{prefs.id}/toggle_all/', 
                          {'enable': True}, format='json')
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Toggled all notifications successfully")
        print(f"   Message: {data.get('message')}")
        results.append(("Toggle Notifications", True))
    else:
        print(f"❌ Failed: {response.data if hasattr(response, 'data') else response.content}")
        results.append(("Toggle Notifications", False))
    
    return results

def test_email_logs(client):
    """Test email logs viewing"""
    print_header("EMAIL LOGS")
    results = []
    
    # Test 4: Get email logs
    print_test(4, "Get Email Logs")
    response = client.get('/api/v1/notifications/email-logs/')
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
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
                
                status_icon = {
                    'SENT': '✅',
                    'PENDING': '⏳',
                    'FAILED': '❌',
                }.get(status, '❓')
                
                print(f"  {i}. {status_icon} {template} - {status}")
                print(f"     Subject: {subject[:50]}")
        
        results.append(("Get Email Logs", True))
    else:
        print(f"❌ Failed: {response.data if hasattr(response, 'data') else response.content}")
        results.append(("Get Email Logs", False))
    
    # Test 5: Filter email logs
    print_test(5, "Filter Email Logs")
    response = client.get('/api/v1/notifications/email-logs/', {'status': 'SENT'})
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, dict) and 'results' in data:
            total = data.get('count', 0)
        else:
            total = len(data)
        
        print(f"✅ Found {total} sent emails")
        results.append(("Filter Email Logs", True))
    else:
        print(f"❌ Failed")
        results.append(("Filter Email Logs", False))
    
    return results

def test_email_statistics(client):
    """Test email statistics endpoint"""
    print_header("EMAIL STATISTICS")
    results = []
    
    # Test 6: Global statistics
    print_test(6, "Get Global Email Statistics")
    response = client.get('/api/v1/notifications/email-logs/stats/')
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Retrieved email statistics")
        print(f"\n📊 Overall Statistics:")
        print(f"   Total Emails: {data.get('total', 0)}")
        print(f"   Sent: {data.get('sent', 0)}")
        print(f"   Pending: {data.get('pending', 0)}")
        print(f"   Failed: {data.get('failed', 0)}")
        print(f"   Success Rate: {data.get('success_rate', 0)}%")
        
        by_template = data.get('by_template_type', {})
        if by_template:
            print(f"\n📧 By Template Type:")
            for template, count in by_template.items():
                print(f"   {template}: {count}")
        
        results.append(("Global Statistics", True))
    else:
        print(f"❌ Failed")
        results.append(("Global Statistics", False))
    
    # Test 7: User statistics
    print_test(7, "Get User Email Statistics")
    response = client.get('/api/v1/notifications/email-logs/user_stats/')
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Retrieved user email statistics")
        print(f"\n👤 Your Email Statistics:")
        print(f"   Total: {data.get('total', 0)}")
        print(f"   Sent: {data.get('sent', 0)}")
        print(f"   Pending: {data.get('pending', 0)}")
        print(f"   Failed: {data.get('failed', 0)}")
        
        recent = data.get('recent_emails', [])
        if recent:
            print(f"\n📧 Recent Emails ({len(recent)}):")
            for email in recent[:3]:
                print(f"   - {email.get('subject')} ({email.get('status')})")
        
        results.append(("User Statistics", True))
    else:
        print(f"❌ Failed")
        results.append(("User Statistics", False))
    
    return results

def test_email_templates():
    """Test email templates"""
    print_header("EMAIL TEMPLATES")
    
    print_test(8, "Check Email Templates")
    templates = EmailTemplate.objects.filter(is_active=True)
    print(f"✅ Found {templates.count()} active templates:")
    
    for template in templates:
        print(f"   📧 {template.name} ({template.template_type})")
    
    return [("Email Templates", templates.count() > 0)]

def main():
    """Main test runner"""
    print("=" * 70)
    print("  EMAIL SYSTEM API TEST (Django Test Client)")
    print("=" * 70)
    print(f"📅 Testing email system endpoints")
    print(f"📧 Test Email: tapyze@gmail.com")
    
    # Setup
    user, client = setup_test_user()
    
    # Track results
    all_results = []
    
    try:
        # Run tests
        all_results.extend(test_email_preferences(client))
        all_results.extend(test_email_logs(client))
        all_results.extend(test_email_statistics(client))
        all_results.extend(test_email_templates())
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return 1
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in all_results if result)
    total = len(all_results)
    
    print(f"Results: {passed}/{total} tests passed\n")
    
    for test_name, test_passed in all_results:
        status = "✅ PASS" if test_passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print("\n" + "=" * 70)
    
    if passed == total:
        print("✅ ALL TESTS PASSED!")
        print("\n📋 Available API Endpoints:")
        print("   GET    /api/v1/notifications/email-preferences/")
        print("   GET    /api/v1/notifications/email-preferences/{id}/")
        print("   PATCH  /api/v1/notifications/email-preferences/{id}/")
        print("   POST   /api/v1/notifications/email-preferences/{id}/toggle_all/")
        print("   GET    /api/v1/notifications/email-logs/")
        print("   GET    /api/v1/notifications/email-logs/{id}/")
        print("   GET    /api/v1/notifications/email-logs/stats/")
        print("   GET    /api/v1/notifications/email-logs/user_stats/")
        print("\n💡 Email system is fully functional and ready to use!")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Check output above.")
    
    print("=" * 70)
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
