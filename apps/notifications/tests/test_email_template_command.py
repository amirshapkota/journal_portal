from django.core.management import call_command
from django.test import TestCase

from apps.notifications.models import EmailTemplate


class EmailTemplateCommandTests(TestCase):
    def test_addon_templates_are_seeded_and_idempotent(self):
        expected_types = {
            'SUBMISSION_FIRST_ACKNOWLEDGEMENT',
            'SUBMISSION_PRE_REVIEW_CORRECTION',
            'SUBMISSION_REVIEW_STARTED',
            'SUBMISSION_COPYEDITING_DISCUSSION',
            'SUBMISSION_PRODUCTION_PROOFREADING',
            'EDITORIAL_ASSIGNMENT_SECTION_EDITOR',
            'EDITORIAL_ASSIGNMENT_GUEST_EDITOR',
            'REVIEW_EDITORIAL_ASSIGNMENT',
            'REVIEW_ARTICLE_REQUEST',
            'REVIEW_UNABLE_TO_REVIEW',
            'REVIEW_REQUEST_CANCELLED',
            'REVIEW_EDITOR_DECISION_NOTICE',
            'COPYEDITING_EDITORIAL_ASSIGNMENT',
            'COPYEDITING_REQUEST',
        }

        call_command('create_email_templates')
        first_count = EmailTemplate.objects.filter(template_type__in=expected_types).count()
        self.assertEqual(first_count, len(expected_types))

        call_command('create_email_templates')
        second_count = EmailTemplate.objects.filter(template_type__in=expected_types).count()
        self.assertEqual(second_count, len(expected_types))

        for template in EmailTemplate.objects.filter(template_type__in=expected_types):
            self.assertTrue(template.is_active)
            self.assertTrue(template.subject)
            self.assertTrue(template.html_body)
