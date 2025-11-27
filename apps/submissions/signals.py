"""
Django signals for the submissions app.

Automatically logs submission-related activities.
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from apps.submissions.models import Submission, Document, DocumentVersion
from apps.common.utils.activity_logger import log_user_action, log_system_action
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Submission)
def log_submission_activity(sender, instance, created, **kwargs):
    """
    Log submission creation and updates.
    """
    try:
        user = instance.corresponding_author.user if instance.corresponding_author else None
        
        if created:
            # Log submission creation
            log_user_action(
                user=user,
                action_type='CREATE',
                resource_type='SUBMISSION',
                resource_id=instance.id,
                metadata={
                    'title': instance.title,
                    'journal': instance.journal.name if instance.journal else None,
                    'status': instance.status
                }
            )
            logger.info(f"Logged CREATE SUBMISSION for {instance.id}")
        else:
            # Check if status changed to track specific events
            if hasattr(instance, '_previous_status'):
                old_status = instance._previous_status
                new_status = instance.status
                
                if old_status != new_status:
                    # Map status changes to actions
                    if new_status == 'SUBMITTED':
                        action_type = 'SUBMIT'
                    elif new_status == 'PUBLISHED':
                        action_type = 'PUBLISH'
                    elif new_status == 'WITHDRAWN':
                        action_type = 'WITHDRAW'
                    elif new_status == 'ACCEPTED':
                        action_type = 'APPROVE'
                    elif new_status == 'REJECTED':
                        action_type = 'REJECT'
                    else:
                        action_type = 'UPDATE'
                    
                    log_user_action(
                        user=user,
                        action_type=action_type,
                        resource_type='SUBMISSION',
                        resource_id=instance.id,
                        metadata={
                            'title': instance.title,
                            'old_status': old_status,
                            'new_status': new_status
                        }
                    )
                    logger.info(f"Logged {action_type} SUBMISSION for {instance.id}")
            else:
                # General update
                log_user_action(
                    user=user,
                    action_type='UPDATE',
                    resource_type='SUBMISSION',
                    resource_id=instance.id,
                    metadata={
                        'title': instance.title,
                        'status': instance.status
                    }
                )
    except Exception as e:
        logger.error(f"Failed to log submission activity: {e}")


@receiver(post_save, sender=Document)
def log_document_activity(sender, instance, created, **kwargs):
    """
    Log document creation.
    """
    try:
        if created:
            user = instance.submission.corresponding_author.user if instance.submission and instance.submission.corresponding_author else None
            
            log_user_action(
                user=user,
                action_type='CREATE',
                resource_type='DOCUMENT',
                resource_id=instance.id,
                metadata={
                    'document_type': instance.document_type,
                    'submission_id': str(instance.submission.id) if instance.submission else None
                }
            )
            logger.info(f"Logged CREATE DOCUMENT for {instance.id}")
    except Exception as e:
        logger.error(f"Failed to log document activity: {e}")


@receiver(post_save, sender=DocumentVersion)
def log_document_version_activity(sender, instance, created, **kwargs):
    """
    Log document version creation.
    """
    try:
        if created:
            user = instance.created_by.user if instance.created_by else None
            
            log_user_action(
                user=user,
                action_type='CREATE',
                resource_type='DOCUMENT',
                resource_id=instance.document.id,
                metadata={
                    'version_number': instance.version_number,
                    'file_name': instance.file_name,
                    'file_size': instance.file_size
                }
            )
            logger.info(f"Logged CREATE DOCUMENT VERSION for {instance.id}")
    except Exception as e:
        logger.error(f"Failed to log document version activity: {e}")


@receiver(pre_delete, sender=Document)
def log_document_deletion(sender, instance, **kwargs):
    """
    Log document deletion.
    """
    try:
        user = instance.submission.corresponding_author.user if instance.submission and instance.submission.corresponding_author else None
        
        log_user_action(
            user=user,
            action_type='DELETE',
            resource_type='DOCUMENT',
            resource_id=instance.id,
            metadata={
                'document_type': instance.document_type,
                'submission_id': str(instance.submission.id) if instance.submission else None
            }
        )
        logger.info(f"Logged DELETE DOCUMENT for {instance.id}")
    except Exception as e:
        logger.error(f"Failed to log document deletion: {e}")


# Track status changes
@receiver(post_save, sender=Submission)
def track_submission_status(sender, instance, **kwargs):
    """
    Track the previous status for comparison.
    This runs before log_submission_activity.
    """
    if instance.pk:
        try:
            old_instance = Submission.objects.get(pk=instance.pk)
            instance._previous_status = old_instance.status
        except Submission.DoesNotExist:
            instance._previous_status = None
