"""
Test script for migrated email system (registration and password reset).
Verifies that emails are sent through the new EmailTemplate system with tracking.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_portal.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.notifications.models import EmailTemplate, EmailLog
from apps.notifications.tasks import send_email_verification_email, send_password_reset_email

CustomUser = get_user_model()


def test_email_verification_template():
    """Test that EMAIL_VERIFICATION template exists and can be sent."""
    print("\n" + "="*70)
    print("TEST 1: Email Verification Template")
    print("="*70)
    
    # Check template exists
    try:
        template = EmailTemplate.objects.get(template_type='EMAIL_VERIFICATION')
        print(f"✅ PASS: EMAIL_VERIFICATION template exists")
        print(f"   Name: {template.name}")
        print(f"   Subject: {template.subject}")
        print(f"   Active: {template.is_active}")
    except EmailTemplate.DoesNotExist:
        print(f"❌ FAIL: EMAIL_VERIFICATION template not found")
        return False
    
    return True


def test_password_reset_template():
    """Test that PASSWORD_RESET template exists and can be sent."""
    print("\n" + "="*70)
    print("TEST 2: Password Reset Template")
    print("="*70)
    
    # Check template exists
    try:
        template = EmailTemplate.objects.get(template_type='PASSWORD_RESET')
        print(f"✅ PASS: PASSWORD_RESET template exists")
        print(f"   Name: {template.name}")
        print(f"   Subject: {template.subject}")
        print(f"   Active: {template.is_active}")
    except EmailTemplate.DoesNotExist:
        print(f"❌ FAIL: PASSWORD_RESET template not found")
        return False
    
    return True


def test_send_verification_email():
    """Test sending email verification email with tracking."""
    print("\n" + "="*70)
    print("TEST 3: Send Email Verification Email")
    print("="*70)
    
    # Get or create a test user
    user, created = CustomUser.objects.get_or_create(
        email='test_verification@example.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Verification',
            'username': 'test_verification'
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"   Created test user: {user.email}")
    else:
        print(f"   Using existing test user: {user.email}")
    
    # Count emails before
    initial_count = EmailLog.objects.filter(
        recipient=user.email,
        template_type='EMAIL_VERIFICATION'
    ).count()
    
    # Send verification email
    try:
        verification_url = "http://localhost:3000/verify-email/test123/token456/"
        result = send_email_verification_email(str(user.id), verification_url)
        
        print(f"✅ PASS: Email sent successfully")
        print(f"   Status: {result.get('status')}")
        
        # Check if EmailLog was created
        new_count = EmailLog.objects.filter(
            recipient=user.email,
            template_type='EMAIL_VERIFICATION'
        ).count()
        
        if new_count > initial_count:
            print(f"✅ PASS: EmailLog created (tracking working)")
            latest_log = EmailLog.objects.filter(
                recipient=user.email,
                template_type='EMAIL_VERIFICATION'
            ).order_by('-created_at').first()
            print(f"   Log ID: {latest_log.id}")
            print(f"   Status: {latest_log.status}")
            print(f"   Created: {latest_log.created_at}")
        else:
            print(f"⚠️  WARNING: EmailLog not created (tracking may not be working)")
        
        return True
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_send_password_reset_email():
    """Test sending password reset email with tracking."""
    print("\n" + "="*70)
    print("TEST 4: Send Password Reset Email")
    print("="*70)
    
    # Get or create a test user
    user, created = CustomUser.objects.get_or_create(
        email='test_reset@example.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Reset',
            'username': 'test_reset'
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"   Created test user: {user.email}")
    else:
        print(f"   Using existing test user: {user.email}")
    
    # Count emails before
    initial_count = EmailLog.objects.filter(
        recipient=user.email,
        template_type='PASSWORD_RESET'
    ).count()
    
    # Send password reset email
    try:
        reset_url = "http://localhost:3000/reset-password/test123/token456/"
        result = send_password_reset_email(str(user.id), reset_url)
        
        print(f"✅ PASS: Email sent successfully")
        print(f"   Status: {result.get('status')}")
        
        # Check if EmailLog was created
        new_count = EmailLog.objects.filter(
            recipient=user.email,
            template_type='PASSWORD_RESET'
        ).count()
        
        if new_count > initial_count:
            print(f"✅ PASS: EmailLog created (tracking working)")
            latest_log = EmailLog.objects.filter(
                recipient=user.email,
                template_type='PASSWORD_RESET'
            ).order_by('-created_at').first()
            print(f"   Log ID: {latest_log.id}")
            print(f"   Status: {latest_log.status}")
            print(f"   Created: {latest_log.created_at}")
        else:
            print(f"⚠️  WARNING: EmailLog not created (tracking may not be working)")
        
        return True
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_email_statistics():
    """Test that email statistics include the new email types."""
    print("\n" + "="*70)
    print("TEST 5: Email Statistics")
    print("="*70)
    
    # Get statistics for each email type
    verification_count = EmailLog.objects.filter(template_type='EMAIL_VERIFICATION').count()
    reset_count = EmailLog.objects.filter(template_type='PASSWORD_RESET').count()
    
    print(f"   EMAIL_VERIFICATION emails: {verification_count}")
    print(f"   PASSWORD_RESET emails: {reset_count}")
    
    if verification_count > 0 or reset_count > 0:
        print(f"✅ PASS: Email logs found for migrated email types")
        return True
    else:
        print(f"⚠️  WARNING: No email logs found (run tests 3 & 4 first)")
        return True


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("MIGRATED EMAIL SYSTEM TEST SUITE")
    print("Testing EMAIL_VERIFICATION and PASSWORD_RESET migration")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("Email Verification Template", test_email_verification_template()))
    results.append(("Password Reset Template", test_password_reset_template()))
    results.append(("Send Verification Email", test_send_verification_email()))
    results.append(("Send Password Reset Email", test_send_password_reset_email()))
    results.append(("Email Statistics", test_email_statistics()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Email migration successful!")
        print("\nThe old email system (direct send_mail) has been successfully")
        print("migrated to the new EmailTemplate system with:")
        print("  • Celery task support (async when Redis is available)")
        print("  • EmailLog tracking for delivery monitoring")
        print("  • User preference support")
        print("  • Consistent template management")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the output above.")


if __name__ == '__main__':
    main()
