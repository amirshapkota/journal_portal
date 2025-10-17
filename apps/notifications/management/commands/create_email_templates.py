"""
Management command to create initial email templates.
Run with: python manage.py create_email_templates
"""
from django.core.management.base import BaseCommand
from apps.notifications.models import EmailTemplate
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Create initial email templates from template files'

    def handle(self, *args, **options):
        templates = [
            {
                'template_type': 'EMAIL_VERIFICATION',
                'name': 'Email Verification',
                'subject': 'Verify Your Email Address - {{ site_name }}',
                'description': 'Sent when a new user registers to verify their email address',
                'html_file': 'email_verification.html',
            },
            {
                'template_type': 'PASSWORD_RESET',
                'name': 'Password Reset',
                'subject': 'Password Reset Request - {{ site_name }}',
                'description': 'Sent when a user requests to reset their password',
                'html_file': 'password_reset.html',
            },
            {
                'template_type': 'VERIFICATION_SUBMITTED',
                'name': 'Verification Request Submitted',
                'subject': 'Verification Request Submitted - {{ requested_role }}',
                'description': 'Sent when a user submits a verification request',
                'html_file': 'verification_submitted.html',
            },
            {
                'template_type': 'VERIFICATION_APPROVED',
                'name': 'Verification Approved',
                'subject': 'Congratulations! Your {{ requested_role }} Verification is Approved',
                'description': 'Sent when a verification request is approved',
                'html_file': 'verification_approved.html',
            },
            {
                'template_type': 'VERIFICATION_REJECTED',
                'name': 'Verification Not Approved',
                'subject': 'Update on Your {{ requested_role }} Verification Request',
                'description': 'Sent when a verification request is rejected',
                'html_file': 'verification_rejected.html',
            },
            {
                'template_type': 'VERIFICATION_INFO_REQUESTED',
                'name': 'Additional Information Required',
                'subject': 'Additional Information Needed - {{ requested_role }} Verification',
                'description': 'Sent when admin requests additional information',
                'html_file': 'verification_info_requested.html',
            },
            {
                'template_type': 'ORCID_CONNECTED',
                'name': 'ORCID Connected',
                'subject': 'ORCID Successfully Connected to Your Account',
                'description': 'Sent when user connects their ORCID iD',
                'html_file': 'orcid_connected.html',
            },
            # Phase 4: Review System Templates
            {
                'template_type': 'REVIEW_INVITATION',
                'name': 'Review Invitation',
                'subject': 'Invitation to Review Manuscript - {{ submission_title }}',
                'description': 'Sent when a reviewer is invited to review a manuscript',
                'html_file': 'review_invitation.html',
            },
            {
                'template_type': 'REVIEW_REMINDER',
                'name': 'Review Deadline Reminder',
                'subject': 'Reminder: Review Due Soon - {{ submission_title }}',
                'description': 'Sent to remind reviewers of approaching deadlines',
                'html_file': 'review_reminder.html',
            },
            {
                'template_type': 'REVIEW_SUBMITTED',
                'name': 'Review Submitted Confirmation',
                'subject': 'Review Successfully Submitted - {{ submission_title }}',
                'description': 'Sent when a reviewer submits their review',
                'html_file': 'review_submitted.html',
            },
            {
                'template_type': 'EDITORIAL_DECISION_ACCEPT',
                'name': 'Manuscript Accepted',
                'subject': 'Congratulations! Your Manuscript Has Been Accepted',
                'description': 'Sent when a manuscript is accepted for publication',
                'html_file': 'editorial_decision_accept.html',
            },
            {
                'template_type': 'EDITORIAL_DECISION_REJECT',
                'name': 'Manuscript Not Accepted',
                'subject': 'Decision on Your Manuscript - {{ submission_title }}',
                'description': 'Sent when a manuscript is rejected',
                'html_file': 'editorial_decision_reject.html',
            },
            {
                'template_type': 'REVISION_REQUESTED',
                'name': 'Revisions Requested',
                'subject': 'Revisions Required - {{ submission_title }}',
                'description': 'Sent when revisions are requested for a manuscript',
                'html_file': 'revision_requested.html',
            },
            # Phase 4.3: Editorial Decision Making Templates
            {
                'template_type': 'DECISION_ACCEPT',
                'name': 'Editorial Decision: Accepted',
                'subject': '🎉 Manuscript Accepted - {{ submission_title }}',
                'description': 'Sent when editorial decision is ACCEPT',
                'html_file': 'decision_accept.html',
            },
            {
                'template_type': 'DECISION_REJECT',
                'name': 'Editorial Decision: Not Accepted',
                'subject': 'Editorial Decision - {{ submission_title }}',
                'description': 'Sent when editorial decision is REJECT',
                'html_file': 'decision_reject.html',
            },
            {
                'template_type': 'DECISION_MINOR_REVISION',
                'name': 'Editorial Decision: Minor Revisions',
                'subject': 'Minor Revisions Required - {{ submission_title }}',
                'description': 'Sent when editorial decision is MINOR_REVISION',
                'html_file': 'decision_minor_revision.html',
            },
            {
                'template_type': 'DECISION_MAJOR_REVISION',
                'name': 'Editorial Decision: Major Revisions',
                'subject': 'Major Revisions Required - {{ submission_title }}',
                'description': 'Sent when editorial decision is MAJOR_REVISION',
                'html_file': 'decision_major_revision.html',
            },
            {
                'template_type': 'REVISION_REQUEST',
                'name': 'Revision Request Notification',
                'subject': '{{ revision_type }} Revision Request - {{ submission_title }}',
                'description': 'Sent when a revision round is created',
                'html_file': 'revision_request.html',
            },
            {
                'template_type': 'REVISION_SUBMITTED',
                'name': 'Revision Submitted (Editor)',
                'subject': 'Author Submitted Revisions - {{ submission_title }}',
                'description': 'Sent to editor when author submits revised manuscript',
                'html_file': 'revision_submitted.html',
            },
            {
                'template_type': 'REVISION_APPROVED',
                'name': 'Revision Approved',
                'subject': '✅ Your Revision Has Been Approved - {{ submission_title }}',
                'description': 'Sent when editor approves a revised manuscript',
                'html_file': 'revision_approved.html',
            },
            {
                'template_type': 'REVISION_REJECTED',
                'name': 'Revision Not Accepted',
                'subject': 'Revision Decision - {{ submission_title }}',
                'description': 'Sent when editor rejects a revised manuscript',
                'html_file': 'revision_rejected.html',
            },
        ]

        templates_dir = os.path.join(settings.BASE_DIR, 'templates', 'emails')
        
        created_count = 0
        updated_count = 0
        
        for template_data in templates:
            html_file_path = os.path.join(templates_dir, template_data['html_file'])
            
            # Read HTML content
            try:
                with open(html_file_path, 'r', encoding='utf-8') as f:
                    html_body = f.read()
            except FileNotFoundError:
                self.stdout.write(
                    self.style.WARNING(f"Template file not found: {html_file_path}")
                )
                continue
            
            # Create or update template
            template, created = EmailTemplate.objects.update_or_create(
                template_type=template_data['template_type'],
                defaults={
                    'name': template_data['name'],
                    'subject': template_data['subject'],
                    'html_body': html_body,
                    'text_body': '',  # Will be auto-generated from HTML
                    'description': template_data['description'],
                    'is_active': True,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created template: {template_data['name']}")
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Updated template: {template_data['name']}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary: {created_count} created, {updated_count} updated"
            )
        )
