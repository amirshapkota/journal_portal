"""
Django signals for the reviews app.

Automatically logs review-related activities.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.reviews.models import ReviewAssignment, Review, EditorialDecision
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
        # Use the direct reviewer field from the Review model
        user = instance.reviewer.user if instance.reviewer else None
        
        if created:
            # Log review submission
            log_user_action(
                user=user,
                action_type='SUBMIT',
                resource_type='REVIEW',
                resource_id=instance.id,
                metadata={
                    'recommendation': instance.recommendation,
                    'submission_id': str(instance.submission.id) if instance.submission else None,
                    'submission_title': instance.submission.title if instance.submission else None,
                    'overall_score': instance.scores.get('overall') if instance.scores else None,
                    'reviewer_email': user.email if user else None
                }
            )
            logger.info(f"Logged SUBMIT REVIEW for {instance.id} by {user.email if user else 'Unknown'}")
        else:
            # Log review update
            log_user_action(
                user=user,
                action_type='UPDATE',
                resource_type='REVIEW',
                resource_id=instance.id,
                metadata={
                    'recommendation': instance.recommendation,
                    'overall_score': instance.scores.get('overall') if instance.scores else None
                }
            )
            logger.info(f"Logged UPDATE REVIEW for {instance.id}")
    except Exception as e:
        logger.error(f"Failed to log review activity: {e}")


@receiver(post_save, sender=EditorialDecision)
def log_editorial_decision_activity(sender, instance, created, **kwargs):
    """
    Log editorial decision creation.
    This logs the EDITOR who made the decision, not the submission author.
    """
    try:
        if created:
            editor = instance.decided_by.user if instance.decided_by else None
            
            # Map decision type to action type
            action_type_map = {
                'ACCEPT': 'APPROVE',
                'REJECT': 'REJECT',
                'MINOR_REVISION': 'UPDATE',
                'MAJOR_REVISION': 'UPDATE',
            }
            action_type = action_type_map.get(instance.decision_type, 'UPDATE')
            
            log_user_action(
                user=editor,
                action_type=action_type,
                resource_type='SUBMISSION',
                resource_id=instance.submission.id,
                metadata={
                    'decision_type': instance.decision_type,
                    'decision_display': instance.get_decision_type_display(),
                    'submission_title': instance.submission.title,
                    'submission_author': instance.submission.corresponding_author.user.email if instance.submission.corresponding_author else None,
                    'decision_id': str(instance.id)
                }
            )
            logger.info(f"Logged {action_type} EDITORIAL_DECISION for submission {instance.submission.id} by editor {editor.email if editor else 'Unknown'}")
    except Exception as e:
        logger.error(f"Failed to log editorial decision activity: {e}")


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
