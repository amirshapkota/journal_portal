"""
Django signals for the reviews app.

Automatically logs review-related activities.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.reviews.models import ReviewAssignment, Review
from apps.common.utils.activity_logger import log_user_action, log_system_action
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ReviewAssignment)
def log_review_assignment_activity(sender, instance, created, **kwargs):
    """
    Log review assignment creation and status changes.
    """
    try:
        if created:
            # Log review assignment creation
            log_system_action(
                action_type='CREATE',
                resource_type='REVIEW',
                resource_id=instance.id,
                metadata={
                    'reviewer_email': instance.reviewer.user.email if instance.reviewer else None,
                    'submission_id': str(instance.submission.id),
                    'submission_title': instance.submission.title,
                    'status': instance.status
                }
            )
            logger.info(f"Logged CREATE REVIEW_ASSIGNMENT for {instance.id}")
        else:
            # Check for status changes
            if hasattr(instance, '_previous_status'):
                old_status = instance._previous_status
                new_status = instance.status
                
                if old_status != new_status:
                    user = instance.reviewer.user if instance.reviewer else None
                    
                    # Log status change
                    if new_status == 'ACCEPTED':
                        action_type = 'APPROVE'
                    elif new_status == 'DECLINED':
                        action_type = 'REJECT'
                    else:
                        action_type = 'UPDATE'
                    
                    log_user_action(
                        user=user,
                        action_type=action_type,
                        resource_type='REVIEW',
                        resource_id=instance.id,
                        metadata={
                            'old_status': old_status,
                            'new_status': new_status,
                            'submission_id': str(instance.submission.id)
                        }
                    )
                    logger.info(f"Logged {action_type} REVIEW_ASSIGNMENT for {instance.id}")
    except Exception as e:
        logger.error(f"Failed to log review assignment activity: {e}")


@receiver(post_save, sender=Review)
def log_review_activity(sender, instance, created, **kwargs):
    """
    Log review submission.
    """
    try:
        user = instance.assignment.reviewer.user if instance.assignment and instance.assignment.reviewer else None
        
        if created:
            # Log review submission
            log_user_action(
                user=user,
                action_type='SUBMIT',
                resource_type='REVIEW',
                resource_id=instance.id,
                metadata={
                    'recommendation': instance.recommendation,
                    'submission_id': str(instance.assignment.submission.id) if instance.assignment else None,
                    'submission_title': instance.assignment.submission.title if instance.assignment else None,
                    'overall_score': instance.overall_score
                }
            )
            logger.info(f"Logged SUBMIT REVIEW for {instance.id}")
        else:
            # Log review update
            log_user_action(
                user=user,
                action_type='UPDATE',
                resource_type='REVIEW',
                resource_id=instance.id,
                metadata={
                    'recommendation': instance.recommendation,
                    'overall_score': instance.overall_score
                }
            )
            logger.info(f"Logged UPDATE REVIEW for {instance.id}")
    except Exception as e:
        logger.error(f"Failed to log review activity: {e}")


# Track status changes for review assignments
@receiver(post_save, sender=ReviewAssignment)
def track_review_assignment_status(sender, instance, **kwargs):
    """
    Track the previous status for comparison.
    """
    if instance.pk:
        try:
            old_instance = ReviewAssignment.objects.get(pk=instance.pk)
            instance._previous_status = old_instance.status
        except ReviewAssignment.DoesNotExist:
            instance._previous_status = None
