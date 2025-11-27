"""
Django signals for common app.

Handles authentication events (login, logout) for activity logging.
"""
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from apps.common.utils.activity_logger import log_activity
import logging

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Log user login events.
    
    Triggered automatically when a user successfully logs in.
    """
    print(f"DEBUG: Signal user_logged_in received for {user.email}")
    try:
        log_activity(
            user=user,
            action_type='LOGIN',
            resource_type='USER',
            resource_id=user.id,
            metadata={
                'email': user.email,
                'login_method': 'web'
            },
            request=request
        )
        logger.info(f"Logged LOGIN activity for user {user.email}")
        print(f"DEBUG: Successfully logged login for {user.email}")
    except Exception as e:
        logger.error(f"Failed to log LOGIN activity: {e}")
        print(f"DEBUG: Failed to log login: {e}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    Log user logout events.
    
    Triggered automatically when a user logs out.
    """
    try:
        if user:
            log_activity(
                user=user,
                action_type='LOGOUT',
                resource_type='USER',
                resource_id=user.id,
                metadata={
                    'email': user.email
                },
                request=request
            )
            logger.info(f"Logged LOGOUT activity for user {user.email}")
    except Exception as e:
        logger.error(f"Failed to log LOGOUT activity: {e}")


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """
    Log failed login attempts.
    """
    try:
        email = credentials.get('username') or credentials.get('email', 'unknown')
        
        log_activity(
            user=None,
            action_type='LOGIN',
            resource_type='USER',
            resource_id='failed',
            metadata={
                'email': email,
                'status': 'failed',
                'reason': 'invalid_credentials'
            },
            request=request,
            actor_type='USER'
        )
        logger.warning(f"Logged failed LOGIN attempt for {email}")
    except Exception as e:
        logger.error(f"Failed to log failed LOGIN activity: {e}")
