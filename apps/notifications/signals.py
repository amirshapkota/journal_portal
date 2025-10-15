"""
Django signals for automatic email notifications.
Triggers emails when key events occur.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='users.VerificationRequest')
def send_verification_status_email(sender, instance, created, **kwargs):
    """
    Send email when verification request status changes.
    
    Triggers:
    - On creation (submitted)
    - On approval
    - On rejection
    - On info request
    """
    from apps.notifications.tasks import (
        send_verification_submitted_email,
        send_verification_approved_email,
        send_verification_rejected_email,
        send_verification_info_requested_email
    )
    
    try:
        # New verification request submitted
        if created:
            send_verification_submitted_email.delay(
                str(instance.user.id),
                str(instance.id)
            )
            logger.info(f"Queued verification submitted email for user {instance.user.email}")
        
        # Status changed to approved
        elif instance.status == 'APPROVED' and instance.reviewed_at:
            # Check if this is a recent approval (to avoid re-sending on every save)
            from django.utils import timezone
            from datetime import timedelta
            if instance.reviewed_at > timezone.now() - timedelta(minutes=5):
                send_verification_approved_email.delay(
                    str(instance.user.id),
                    str(instance.id)
                )
                logger.info(f"Queued verification approved email for user {instance.user.email}")
        
        # Status changed to rejected
        elif instance.status == 'REJECTED' and instance.reviewed_at:
            from django.utils import timezone
            from datetime import timedelta
            if instance.reviewed_at > timezone.now() - timedelta(minutes=5):
                send_verification_rejected_email.delay(
                    str(instance.user.id),
                    str(instance.id)
                )
                logger.info(f"Queued verification rejected email for user {instance.user.email}")
        
        # Additional info requested
        elif instance.status == 'INFO_REQUESTED' and instance.additional_info_requested:
            send_verification_info_requested_email.delay(
                str(instance.user.id),
                str(instance.id)
            )
            logger.info(f"Queued verification info requested email for user {instance.user.email}")
    
    except Exception as exc:
        logger.error(f"Error in verification email signal: {exc}")


@receiver(post_save, sender='integrations.ORCIDIntegration')
def send_orcid_connection_email(sender, instance, created, **kwargs):
    """
    Send email when ORCID is connected.
    """
    from apps.notifications.tasks import send_orcid_connected_email
    
    try:
        # New ORCID connection
        if created and instance.orcid_id:
            send_orcid_connected_email.delay(
                str(instance.user.id),
                instance.orcid_id
            )
            logger.info(f"Queued ORCID connected email for user {instance.user.email}")
    
    except Exception as exc:
        logger.error(f"Error in ORCID email signal: {exc}")
