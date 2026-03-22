from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from apps.reviews.views import ReviewAssignmentViewSet, EditorialDecisionViewSet
from apps.submissions.views.workflow.views import CopyeditingAssignmentViewSet, ProductionAssignmentViewSet


class WorkflowTriggerWiringTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch('apps.notifications.tasks.send_editorial_assignment_guest_editor_email.delay')
    @patch('apps.notifications.tasks.send_editorial_assignment_section_editor_email.delay')
    @patch('apps.notifications.tasks.send_submission_review_started_email.delay')
    @patch('apps.notifications.tasks.send_review_editorial_assignment_email.delay')
    @patch('apps.notifications.tasks.send_review_article_request_email.delay')
    @patch('apps.notifications.tasks.send_review_invitation_email.delay')
    def test_review_assignment_perform_create_enqueues_notifications(
        self,
        invitation_delay,
        article_request_delay,
        editorial_assignment_delay,
        review_started_delay,
        section_editor_delay,
        guest_editor_delay,
    ):
        assignment = SimpleNamespace(
            id='assignment-1',
            submission=SimpleNamespace(id='submission-1'),
            assigned_by=SimpleNamespace(id='editor-profile-1'),
        )
        serializer = MagicMock()
        serializer.save.return_value = assignment

        view = ReviewAssignmentViewSet()
        view.perform_create(serializer)

        invitation_delay.assert_called_once_with('assignment-1')
        article_request_delay.assert_called_once_with('assignment-1')
        editorial_assignment_delay.assert_called_once_with('assignment-1')
        review_started_delay.assert_called_once_with('submission-1')
        section_editor_delay.assert_called_once_with('submission-1', 'editor-profile-1')
        guest_editor_delay.assert_called_once_with('submission-1', 'editor-profile-1')

    @patch('apps.notifications.tasks.send_review_unable_to_review_email.delay')
    @patch('apps.reviews.views.ReviewInvitationAcceptSerializer')
    def test_decline_action_enqueues_unable_to_review(self, serializer_cls, unable_delay):
        assignment = SimpleNamespace(
            id='assignment-2',
            reviewer=SimpleNamespace(user=SimpleNamespace(email='reviewer@example.com')),
            status='PENDING',
            declined_at=None,
            decline_reason='',
            save=MagicMock(),
        )

        serializer = MagicMock()
        serializer.validated_data = {'decline_reason': 'Conflict of interest'}
        serializer.is_valid.return_value = True
        serializer_cls.return_value = serializer

        request = SimpleNamespace(
            user=assignment.reviewer.user,
            data={'decline_reason': 'Conflict of interest'},
        )

        view = ReviewAssignmentViewSet()
        view.get_object = MagicMock(return_value=assignment)
        view.get_serializer = MagicMock(return_value=SimpleNamespace(data={'id': 'assignment-2'}))

        response = view.decline(request)

        self.assertEqual(response.status_code, 200)
        unable_delay.assert_called_once_with('assignment-2')

    @patch('apps.notifications.tasks.send_review_request_cancelled_email.delay')
    def test_cancel_action_enqueues_cancelled_notification(self, cancelled_delay):
        assignment = SimpleNamespace(
            id='assignment-3',
            status='PENDING',
            save=MagicMock(),
        )

        request = SimpleNamespace(
            user=SimpleNamespace(
                is_staff=True,
                get_full_name=lambda: 'Chief Editor',
                email='editor@example.com',
            ),
            data={'reason': 'Reviewer reassigned'},
        )

        view = ReviewAssignmentViewSet()
        view.get_object = MagicMock(return_value=assignment)
        view.get_serializer = MagicMock(return_value=SimpleNamespace(data={'id': 'assignment-3'}))

        response = view.cancel(request)

        self.assertEqual(response.status_code, 200)
        cancelled_delay.assert_called_once_with('assignment-3', 'Chief Editor', 'Reviewer reassigned')

    @patch('apps.notifications.tasks.send_review_editor_decision_notice_email.delay')
    @patch('apps.notifications.tasks.send_decision_letter_email.delay')
    def test_editorial_decision_perform_create_enqueues_decision_notifications(self, decision_letter_delay, decision_notice_delay):
        submission = SimpleNamespace(status='UNDER_REVIEW', save=MagicMock())
        decision = SimpleNamespace(
            id='decision-1',
            decision_type='ACCEPT',
            submission=submission,
        )
        serializer = MagicMock()
        serializer.save.return_value = decision

        view = EditorialDecisionViewSet()
        view.request = SimpleNamespace(user=SimpleNamespace(profile='editor-profile'))

        view.perform_create(serializer)

        decision_letter_delay.assert_called_once_with('decision-1')
        decision_notice_delay.assert_called_once_with('decision-1')

    @patch('apps.notifications.tasks.send_copyediting_request_email.delay')
    @patch('apps.notifications.tasks.send_copyediting_editorial_assignment_email.delay')
    @patch('apps.notifications.tasks.send_copyediting_assigned_email.delay')
    def test_copyediting_assignment_perform_create_enqueues_assignment_notifications(
        self,
        assigned_delay,
        editorial_assignment_delay,
        request_delay,
    ):
        submission = SimpleNamespace(status='ACCEPTED', save=MagicMock())
        assignment = SimpleNamespace(id='copy-1', submission=submission)
        serializer = MagicMock()
        serializer.save.return_value = assignment

        view = CopyeditingAssignmentViewSet()
        view.perform_create(serializer)

        assigned_delay.assert_called_once_with('copy-1')
        editorial_assignment_delay.assert_called_once_with('copy-1')
        request_delay.assert_called_once_with('copy-1')

    @patch('apps.notifications.tasks.send_production_assigned_email.delay')
    def test_production_assignment_perform_create_enqueues_assignment_notification(self, assigned_delay):
        submission = SimpleNamespace(status='COPYEDITING', save=MagicMock())
        assignment = SimpleNamespace(id='prod-1', submission=submission)
        serializer = MagicMock()
        serializer.save.return_value = assignment

        view = ProductionAssignmentViewSet()
        view.perform_create(serializer)

        assigned_delay.assert_called_once_with('prod-1')
