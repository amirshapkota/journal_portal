"""
Celery tasks for email notifications.
Handles async email sending with retry logic.
"""
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_email_task(self, email_log_id):
    """
    Send an email using the EmailLog record.
    Retries up to 3 times with 5 minute delays.
    """
    from apps.notifications.models import EmailLog
    
    try:
        email_log = EmailLog.objects.get(id=email_log_id)
        
        # Create email message
        email = EmailMultiAlternatives(
            subject=email_log.subject,
            body=email_log.body_text or '',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_log.recipient],
        )
        
        # Add HTML version if available
        if email_log.body_html:
            email.attach_alternative(email_log.body_html, "text/html")
        
        # Send email
        email.send(fail_silently=False)
        
        # Update log
        email_log.status = 'SENT'
        email_log.sent_at = timezone.now()
        email_log.save()
        
        logger.info(f"Email sent successfully to {email_log.recipient} (template: {email_log.template_type})")
        
        return {
            'status': 'success',
            'email_log_id': str(email_log_id),
            'recipient': email_log.recipient
        }
        
    except EmailLog.DoesNotExist:
        logger.error(f"EmailLog {email_log_id} not found")
        return {'status': 'error', 'message': 'EmailLog not found'}
    
    except Exception as exc:
        logger.error(f"Failed to send email {email_log_id}: {exc}")
        
        # Update log with error
        try:
            email_log = EmailLog.objects.get(id=email_log_id)
            email_log.retry_count += 1
            email_log.error_message = str(exc)
            
            if email_log.retry_count >= email_log.max_retries:
                email_log.status = 'FAILED'
                logger.error(f"Email {email_log_id} failed after {email_log.retry_count} retries")
            else:
                email_log.status = 'PENDING'
            
            email_log.save()
        except:
            pass
        
        # Retry task
        raise self.retry(exc=exc)


@shared_task
def send_template_email(recipient, template_type, context, user_id=None):
    """
    Send an email using a template.
    
    Args:
        recipient: Email address
        template_type: Type of email template to use
        context: Dictionary of template variables
        user_id: Optional user ID (for preference checking)
    """
    from apps.notifications.models import EmailTemplate, EmailLog, EmailNotificationPreference
    from django.contrib.auth import get_user_model
    
    CustomUser = get_user_model()
    
    try:
        # Check user preferences if user_id provided
        if user_id:
            try:
                user = CustomUser.objects.get(id=user_id)
                prefs, _ = EmailNotificationPreference.objects.get_or_create(user=user)
                
                # Check if notifications are globally disabled
                if not prefs.email_notifications_enabled:
                    logger.info(f"Email notifications disabled for user {user.email}")
                    return {'status': 'skipped', 'reason': 'notifications_disabled'}
                
                # Check specific preference based on template type
                preference_map = {
                    'ORCID_CONNECTED': 'email_on_orcid_connected',
                    'ORCID_DISCONNECTED': 'email_on_orcid_disconnected',
                    'VERIFICATION_SUBMITTED': 'email_on_verification_submitted',
                    'VERIFICATION_APPROVED': 'email_on_verification_approved',
                    'VERIFICATION_REJECTED': 'email_on_verification_rejected',
                    'VERIFICATION_INFO_REQUESTED': 'email_on_verification_info_requested',
                }
                
                pref_field = preference_map.get(template_type)
                if pref_field and not getattr(prefs, pref_field, True):
                    logger.info(f"Email type {template_type} disabled for user {user.email}")
                    return {'status': 'skipped', 'reason': 'preference_disabled'}
                    
            except CustomUser.DoesNotExist:
                pass
        
        # Get template
        template = EmailTemplate.objects.get(
            template_type=template_type,
            is_active=True
        )
        
        # Render subject and body
        from django.template import Template, Context
        
        subject_template = Template(template.subject)
        subject = subject_template.render(Context(context))
        
        html_template = Template(template.html_body)
        html_body = html_template.render(Context(context))
        
        # Generate text body if not provided
        if template.text_body:
            text_template = Template(template.text_body)
            text_body = text_template.render(Context(context))
        else:
            # Strip HTML for text version
            from django.utils.html import strip_tags
            text_body = strip_tags(html_body)
        
        # Create email log
        email_log = EmailLog.objects.create(
            recipient=recipient,
            user_id=user_id,
            template_type=template_type,
            subject=subject,
            body_html=html_body,
            body_text=text_body,
            context_data=context,
            status='PENDING'
        )
        
        # Try to queue email for sending with Celery, fallback to direct send
        try:
            send_email_task.delay(str(email_log.id))
            logger.info(f"Email queued: {template_type} to {recipient}")
            return {
                'status': 'queued',
                'email_log_id': str(email_log.id),
                'recipient': recipient,
                'template_type': template_type
            }
        except Exception as celery_exc:
            # Celery not available (Redis not running), send directly
            logger.warning(f"Celery not available, sending email directly: {celery_exc}")
            try:
                from django.core.mail import send_mail
                send_mail(
                    subject,
                    text_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient],
                    html_message=html_body,
                    fail_silently=False,
                )
                email_log.status = 'SENT'
                email_log.save()
                logger.info(f"Email sent directly: {template_type} to {recipient}")
                return {
                    'status': 'sent',
                    'email_log_id': str(email_log.id),
                    'recipient': recipient,
                    'template_type': template_type
                }
            except Exception as send_exc:
                email_log.status = 'FAILED'
                email_log.error_message = str(send_exc)
                email_log.save()
                logger.error(f"Failed to send email directly: {send_exc}")
                raise
        
    except EmailTemplate.DoesNotExist:
        logger.error(f"Email template {template_type} not found")
        return {'status': 'error', 'message': f'Template {template_type} not found'}
    
    except Exception as exc:
        logger.error(f"Error sending template email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_verification_submitted_email(user_id, verification_request_id):
    """Send email when verification request is submitted."""
    from django.contrib.auth import get_user_model
    from apps.users.models import VerificationRequest
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        verification_request = VerificationRequest.objects.get(id=verification_request_id)
        
        context = {
            'user_name': user.profile.display_name or user.email,
            'requested_role': verification_request.get_requested_role_display(),
            'auto_score': verification_request.auto_score,
            'request_id': str(verification_request.id),
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='VERIFICATION_SUBMITTED',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending verification submitted email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_verification_approved_email(user_id, verification_request_id):
    """Send email when verification is approved."""
    from django.contrib.auth import get_user_model
    from apps.users.models import VerificationRequest
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        verification_request = VerificationRequest.objects.get(id=verification_request_id)
        
        context = {
            'user_name': user.profile.display_name or user.email,
            'requested_role': verification_request.get_requested_role_display(),
            'approved_date': verification_request.reviewed_at.strftime('%B %d, %Y') if verification_request.reviewed_at else 'today',
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='VERIFICATION_APPROVED',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending verification approved email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_verification_rejected_email(user_id, verification_request_id):
    """Send email when verification is rejected."""
    from django.contrib.auth import get_user_model
    from apps.users.models import VerificationRequest
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        verification_request = VerificationRequest.objects.get(id=verification_request_id)
        
        context = {
            'user_name': user.profile.display_name or user.email,
            'requested_role': verification_request.get_requested_role_display(),
            'rejection_reason': verification_request.rejection_reason,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='VERIFICATION_REJECTED',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending verification rejected email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_verification_info_requested_email(user_id, verification_request_id):
    """Send email when admin requests additional information."""
    from django.contrib.auth import get_user_model
    from apps.users.models import VerificationRequest
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        verification_request = VerificationRequest.objects.get(id=verification_request_id)
        
        context = {
            'user_name': user.profile.display_name or user.email,
            'requested_role': verification_request.get_requested_role_display(),
            'additional_info_requested': verification_request.additional_info_requested,
            'request_id': str(verification_request.id),
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='VERIFICATION_INFO_REQUESTED',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending verification info requested email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_orcid_connected_email(user_id, orcid_id):
    """Send email when ORCID is connected."""
    from django.contrib.auth import get_user_model
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        
        context = {
            'user_name': user.profile.display_name or user.email,
            'orcid_id': orcid_id,
            'orcid_url': f'https://orcid.org/{orcid_id}',
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='ORCID_CONNECTED',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending ORCID connected email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_email_verification_email(user_id, verification_url):
    """Send email verification link to new user."""
    from django.contrib.auth import get_user_model
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        
        context = {
            'user_name': user.get_full_name() or user.email,
            'user_email': user.email,
            'verification_url': verification_url,
            'site_name': 'Journal Publication Portal',
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='EMAIL_VERIFICATION',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending email verification email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_password_reset_email(user_id, reset_url):
    """Send password reset link to user."""
    from django.contrib.auth import get_user_model
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        
        context = {
            'user_name': user.get_full_name() or user.email,
            'user_email': user.email,
            'reset_url': reset_url,
            'site_name': 'Journal Publication Portal',
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='PASSWORD_RESET',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending password reset email: {exc}")
        return {'status': 'error', 'message': str(exc)}
