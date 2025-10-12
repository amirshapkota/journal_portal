"""
Common utilities for the Journal Portal.
"""
import logging
from typing import Any, Dict
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger('journal_portal')


class EmailService:
    """Service for sending emails."""
    
    @staticmethod
    def send_notification_email(to_email: str, subject: str, message: str) -> bool:
        """Send a notification email."""
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[to_email],
                fail_silently=False,
            )
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False


class AuditLogger:
    """Service for audit logging."""
    
    @staticmethod
    def log_action(user, action: str, resource: str, resource_id: str = None, details: Dict[str, Any] = None):
        """Log user actions for audit purposes."""
        log_data = {
            'user': str(user),
            'action': action,
            'resource': resource,
            'resource_id': resource_id,
            'details': details or {}
        }
        logger.info(f"AUDIT: {log_data}")


class FileValidator:
    """Utility for file validation."""
    
    ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.tex']
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    @classmethod
    def validate_file(cls, file) -> tuple[bool, str]:
        """Validate uploaded file."""
        # Check file extension
        file_ext = file.name.lower().split('.')[-1] if '.' in file.name else ''
        if f'.{file_ext}' not in cls.ALLOWED_EXTENSIONS:
            return False, f"File type not allowed. Allowed types: {', '.join(cls.ALLOWED_EXTENSIONS)}"
        
        # Check file size
        if file.size > cls.MAX_FILE_SIZE:
            return False, f"File too large. Maximum size: {cls.MAX_FILE_SIZE // (1024*1024)}MB"
        
        return True, "File is valid"