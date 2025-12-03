"""
Celery tasks for review management.
Handles background tasks like checking expired deadlines, sending notifications, etc.
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(name='reviews.check_expired_deadlines')
def check_expired_deadlines():
    """
    Periodic task to check and update expired review assignments and revision rounds.
    Should be scheduled to run daily via Celery Beat.
    """
    from apps.reviews.models import ReviewAssignment, RevisionRound
    
    # Check review assignments
    expired_assignments = ReviewAssignment.objects.filter(
        status__in=['PENDING', 'ACCEPTED'],
        due_date__lt=timezone.now()
    )
    
    assignment_count = 0
    for assignment in expired_assignments:
        assignment.status = 'EXPIRED'
        assignment.save()
        assignment_count += 1
        
        # Send notification to editor
        try:
            send_expiration_notification_to_editor(assignment)
        except Exception as e:
            logger.error(f"Failed to send expiration notification for assignment {assignment.id}: {e}")
    
    # Check revision rounds
    expired_revisions = RevisionRound.objects.filter(
        status__in=['REQUESTED', 'IN_PROGRESS'],
        deadline__lt=timezone.now()
    )
    
    revision_count = 0
    for revision in expired_revisions:
        revision.status = 'EXPIRED'
        revision.save()
        
        # Update submission status to REJECTED
        submission = revision.submission
        submission.status = 'REJECTED'
        submission.save()
        revision_count += 1
        
        # Send notification to author and editor
        try:
            send_revision_expiration_notification(revision)
        except Exception as e:
            logger.error(f"Failed to send revision expiration notification for {revision.id}: {e}")
    
    logger.info(f"Expired deadlines check complete: {assignment_count} assignments, {revision_count} revisions")
    return {
        'assignments_expired': assignment_count,
        'revisions_expired': revision_count
    }


@shared_task(name='reviews.send_deadline_reminders')
def send_deadline_reminders():
    """
    Send reminder notifications for upcoming deadlines.
    Run daily to check for deadlines in next 3 days.
    """
    from apps.reviews.models import ReviewAssignment, RevisionRound
    from datetime import timedelta
    
    reminder_threshold = timezone.now() + timedelta(days=3)
    
    # Review assignment reminders
    upcoming_reviews = ReviewAssignment.objects.filter(
        status__in=['PENDING', 'ACCEPTED'],
        due_date__gte=timezone.now(),
        due_date__lte=reminder_threshold
    )
    
    reminder_count = 0
    for assignment in upcoming_reviews:
        try:
            send_review_deadline_reminder(assignment)
            reminder_count += 1
        except Exception as e:
            logger.error(f"Failed to send deadline reminder for assignment {assignment.id}: {e}")
    
    # Revision deadline reminders
    upcoming_revisions = RevisionRound.objects.filter(
        status__in=['REQUESTED', 'IN_PROGRESS'],
        deadline__gte=timezone.now(),
        deadline__lte=reminder_threshold
    )
    
    revision_reminder_count = 0
    for revision in upcoming_revisions:
        try:
            send_revision_deadline_reminder(revision)
            revision_reminder_count += 1
        except Exception as e:
            logger.error(f"Failed to send revision deadline reminder for {revision.id}: {e}")
    
    logger.info(f"Deadline reminders sent: {reminder_count} reviews, {revision_reminder_count} revisions")
    return {
        'review_reminders_sent': reminder_count,
        'revision_reminders_sent': revision_reminder_count
    }


def send_expiration_notification_to_editor(assignment):
    """Send notification to editor when review assignment expires."""
    subject = f"Review Assignment Expired - {assignment.submission.title}"
    message = f"""
    Dear Editor,
    
    The following review assignment has expired:
    
    Submission: {assignment.submission.title}
    Reviewer: {assignment.reviewer.display_name}
    Original Due Date: {assignment.due_date.strftime('%Y-%m-%d')}
    Status: Expired
    
    Please reassign this review or take appropriate action.
    
    Best regards,
    Journal Portal System
    """
    
    recipient_email = assignment.assigned_by.user.email
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email],
        fail_silently=False,
    )


def send_revision_expiration_notification(revision):
    """Send notification when revision deadline expires."""
    submission = revision.submission
    
    if not submission.corresponding_author:
        logger.warning(f"Revision {revision.id} has no corresponding author, skipping expiration notification")
        return
    
    author_email = submission.corresponding_author.user.email
    
    # Notify author
    subject = f"Revision Deadline Expired - {submission.title}"
    message = f"""
    Dear {submission.corresponding_author.display_name},
    
    The revision deadline for your submission has expired:
    
    Submission: {submission.title}
    Deadline: {revision.deadline.strftime('%Y-%m-%d')}
    
    Unfortunately, your submission has been automatically rejected due to missing the revision deadline.
    
    If you believe this is an error or have extenuating circumstances, please contact the editorial office.
    
    Best regards,
    Editorial Team
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [author_email],
        fail_silently=False,
    )


def send_review_deadline_reminder(assignment):
    """Send reminder for upcoming review deadline."""
    days_remaining = (assignment.due_date - timezone.now()).days
    
    subject = f"Review Deadline Reminder - {assignment.submission.title}"
    message = f"""
    Dear {assignment.reviewer.display_name},
    
    This is a reminder that your review is due in {days_remaining} day(s):
    
    Submission: {assignment.submission.title}
    Due Date: {assignment.due_date.strftime('%Y-%m-%d')}
    
    Please complete your review at your earliest convenience.
    
    Best regards,
    Editorial Team
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [assignment.reviewer.user.email],
        fail_silently=False,
    )


def send_revision_deadline_reminder(revision):
    """Send reminder for upcoming revision deadline."""
    days_remaining = (revision.deadline - timezone.now()).days
    
    subject = f"Revision Deadline Reminder - {revision.submission.title}"
    message = f"""
    Dear {revision.submission.corresponding_author.display_name},
    
    This is a reminder that your revision is due in {days_remaining} day(s):
    
    Submission: {revision.submission.title}
    Due Date: {revision.deadline.strftime('%Y-%m-%d')}
    
    Please submit your revised manuscript before the deadline.
    
    Best regards,
    Editorial Team
    """
    
    if not revision.submission.corresponding_author:
        logger.warning(f"Revision {revision.id} has no corresponding author, skipping reminder")
        return
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [revision.submission.corresponding_author.user.email],
        fail_silently=False,
    )
