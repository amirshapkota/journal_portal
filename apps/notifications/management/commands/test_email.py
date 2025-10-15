"""
Management command to test email configuration.
Run with: python manage.py test_email your-email@example.com
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail, get_connection
from django.conf import settings
import sys


class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            type=str,
            help='Email address to send test email to'
        )

    def handle(self, *args, **options):
        recipient = options['recipient']
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("EMAIL CONFIGURATION TEST"))
        self.stdout.write("="*60 + "\n")
        
        # Display current configuration
        self.stdout.write("Current Email Settings:")
        self.stdout.write(f"  Backend: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"  Host: {settings.EMAIL_HOST}")
        self.stdout.write(f"  Port: {settings.EMAIL_PORT}")
        self.stdout.write(f"  Use TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"  User: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"  From: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write("")
        
        # Test 1: Connection Test
        self.stdout.write("Test 1: Testing SMTP Connection...")
        try:
            connection = get_connection()
            connection.open()
            self.stdout.write(self.style.SUCCESS("  ✅ SMTP connection successful!"))
            connection.close()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Connection failed: {e}"))
            self.stdout.write("\n" + self.style.WARNING("Troubleshooting Tips:"))
            self.stdout.write("  1. Check your .env file has correct EMAIL_* settings")
            self.stdout.write("  2. Verify your email credentials")
            self.stdout.write("  3. For Gmail, use App Password, not regular password")
            self.stdout.write("  4. Check firewall/antivirus isn't blocking port 587")
            sys.exit(1)
        
        # Test 2: Send Test Email
        self.stdout.write(f"\nTest 2: Sending test email to {recipient}...")
        try:
            send_mail(
                subject='Journal Portal - Email Configuration Test',
                message='This is a test email from the Journal Portal system.\n\n'
                        'If you received this email, your email configuration is working correctly!\n\n'
                        'Email System Features:\n'
                        '  ✅ Verification notifications\n'
                        '  ✅ ORCID connection alerts\n'
                        '  ✅ Admin notifications\n'
                        '  ✅ User preference management\n\n'
                        'Thank you for using Journal Portal!',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"  ✅ Email sent successfully to {recipient}!"))
            self.stdout.write("\n  Check your inbox (and spam folder) for the test email.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Failed to send email: {e}"))
            sys.exit(1)
        
        # Test 3: Template System Test
        self.stdout.write("\nTest 3: Checking email templates...")
        try:
            from apps.notifications.models import EmailTemplate
            
            templates = EmailTemplate.objects.filter(is_active=True)
            if templates.count() >= 5:
                self.stdout.write(self.style.SUCCESS(f"  ✅ {templates.count()} email templates found"))
                for template in templates:
                    self.stdout.write(f"    - {template.name}")
            else:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠️  Only {templates.count()} templates found. Expected 5."
                ))
                self.stdout.write("    Run: python manage.py create_email_templates")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Template check failed: {e}"))
        
        # Test 4: Celery Configuration
        self.stdout.write("\nTest 4: Checking Celery configuration...")
        try:
            from journal_portal import celery_app
            
            self.stdout.write(self.style.SUCCESS("  ✅ Celery app configured"))
            self.stdout.write(f"    Broker: {settings.CELERY_BROKER_URL}")
            self.stdout.write(f"    Result Backend: {settings.CELERY_RESULT_BACKEND}")
            self.stdout.write("\n  To start Celery worker, run:")
            self.stdout.write("    celery -A journal_portal worker -l info")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ⚠️  Celery check: {e}"))
        
        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("✅ EMAIL SYSTEM TEST COMPLETE"))
        self.stdout.write("="*60)
        self.stdout.write("\nNext Steps:")
        self.stdout.write("  1. Check your email inbox for the test message")
        self.stdout.write("  2. Start Celery worker for async email sending:")
        self.stdout.write("     celery -A journal_portal worker -l info")
        self.stdout.write("  3. Test the full workflow by creating a verification request")
        self.stdout.write("\nFor detailed setup instructions, see:")
        self.stdout.write("  docs/EMAIL_SETUP_GUIDE.md\n")
