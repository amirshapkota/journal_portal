from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.notifications import tasks


class TaskContextTests(SimpleTestCase):
    @patch('apps.notifications.tasks.send_template_email')
    @patch('apps.reviews.models.ReviewAssignment')
    def test_review_request_cancelled_context_contains_required_placeholders(self, review_assignment_model, send_template_email):
        author_user = SimpleNamespace(id='user-author', email='author@example.com', get_full_name=lambda: 'Author User')
        editor_user = SimpleNamespace(id='user-editor', email='editor@example.com', get_full_name=lambda: 'Editor User')
        section_editor_user = SimpleNamespace(id='user-section', email='section@example.com', get_full_name=lambda: 'Section Editor User')
        reviewer_user = SimpleNamespace(id='user-reviewer', email='reviewer@example.com', get_full_name=lambda: 'Reviewer User')

        assignment = SimpleNamespace(
            id='assignment-ctx-1',
            submission=SimpleNamespace(
                id='submission-ctx-1',
                title='Context Test Submission',
                corresponding_author=SimpleNamespace(user=author_user),
                section=SimpleNamespace(section_editor=SimpleNamespace(user=section_editor_user)),
            ),
            reviewer=SimpleNamespace(user=reviewer_user),
            assigned_by=SimpleNamespace(user=editor_user),
        )

        review_assignment_model.objects.select_related.return_value.get.return_value = assignment

        tasks.send_review_request_cancelled_email('assignment-ctx-1', 'Chief Editor', 'Policy update')

        self.assertGreaterEqual(send_template_email.call_count, 1)
        first_context = send_template_email.call_args.kwargs['context']

        required_keys = {
            'recipient_name',
            'recipient_role',
            'submission_title',
            'submission_id',
            'reviewer_name',
            'cancelled_by',
            'cancelled_at',
            'reason',
        }
        self.assertTrue(required_keys.issubset(first_context.keys()))

    @patch('apps.notifications.tasks.send_template_email')
    @patch('apps.journals.models.JournalStaff')
    @patch('apps.submissions.models.models.Submission')
    def test_submission_ack_context_contains_required_placeholders(self, submission_model, journal_staff_model, send_template_email):
        author_user = SimpleNamespace(id='user-ack', email='ack@example.com', get_full_name=lambda: 'Ack Author')
        submission = SimpleNamespace(
            id='submission-ack-1',
            title='Acknowledgement Submission',
            submitted_at=None,
            corresponding_author=SimpleNamespace(user=author_user),
            journal=SimpleNamespace(title='Journal of Tests'),
        )

        submission_model.objects.select_related.return_value.get.return_value = submission
        journal_staff_model.objects.select_related.return_value.filter.return_value = []

        tasks.send_submission_first_acknowledgement_email('submission-ack-1')

        context = send_template_email.call_args.kwargs['context']
        required_keys = {
            'author_name',
            'submission_title',
            'submission_id',
            'journal_name',
            'submitted_at',
            'dashboard_url',
            'editor_name',
        }
        self.assertTrue(required_keys.issubset(context.keys()))
