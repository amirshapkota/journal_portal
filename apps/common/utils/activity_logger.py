"""
Activity logging utilities.

Provides helper functions for logging user activities and system events
to the ActivityLog model.
"""
from apps.common.models import ActivityLog


def get_client_ip(request):
    """
    Extract the client IP address from the request.
    
    Handles proxies and load balancers by checking X-Forwarded-For header.
    
    Args:
        request: Django request object
        
    Returns:
        str: Client IP address or None
    """
    if not request:
        return None
        
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get the first IP in the chain (client IP)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    return ip


def get_user_agent(request):
    """
    Extract the user agent string from the request.
    
    Args:
        request: Django request object
        
    Returns:
        str: User agent string or empty string
    """
    if not request:
        return ''
    
    return request.META.get('HTTP_USER_AGENT', '')


def get_session_id(request):
    """
    Extract the session ID from the request.
    
    Args:
        request: Django request object
        
    Returns:
        str: Session ID or None
    """
    if not request or not hasattr(request, 'session'):
        return None
    
    return request.session.session_key


def log_activity(user, action_type, resource_type, resource_id, 
                metadata=None, request=None, actor_type=None):
    """
    Log an activity to the ActivityLog model.
    
    Main function for creating activity log entries.
    It automatically extracts IP address, user agent, and session ID
    from the request if provided.
    
    Args:
        user: User instance or None for system actions
        action_type: Type of action (LOGIN, CREATE, UPDATE, etc.)
        resource_type: Type of resource (USER, SUBMISSION, REVIEW, etc.)
        resource_id: ID of the resource (as string or UUID)
        metadata: Optional dict of additional data to store
        request: Optional Django request object for extracting IP, user agent, etc.
        actor_type: Optional actor type override (USER, SYSTEM, API, INTEGRATION)
        
    Returns:
        ActivityLog: The created activity log instance
    """
    # Determine actor type
    if actor_type is None:
        if user:
            actor_type = 'USER'
        else:
            actor_type = 'SYSTEM'
    
    # Build log data
    log_data = {
        'user': user,
        'actor_type': actor_type,
        'action_type': action_type,
        'resource_type': resource_type,
        'resource_id': str(resource_id),
        'metadata': metadata or {},
    }
    
    # Extract request information if available
    if request:
        log_data['ip_address'] = get_client_ip(request)
        log_data['user_agent'] = get_user_agent(request)
        log_data['session_id'] = get_session_id(request) or ''
    
    # Create and return the log entry
    try:
        return ActivityLog.objects.create(**log_data)
    except Exception as e:
        # Log the error but don't fail the main operation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create activity log: {e}")
        return None


def log_user_action(user, action_type, resource_type, resource_id, 
                   metadata=None, request=None):
    """
    Convenience function for logging user actions.
    
    Same as log_activity but explicitly sets actor_type to USER.
    """
    return log_activity(
        user=user,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
        request=request,
        actor_type='USER'
    )


def log_system_action(action_type, resource_type, resource_id, metadata=None):
    """
    Convenience function for logging system actions.
    
    Same as log_activity but explicitly sets actor_type to SYSTEM
    and user to None.
    """
    return log_activity(
        user=None,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
        request=None,
        actor_type='SYSTEM'
    )


def log_api_action(action_type, resource_type, resource_id, 
                  metadata=None, request=None):
    """
    Convenience function for logging API actions.
    
    Same as log_activity but explicitly sets actor_type to API.
    """
    return log_activity(
        user=None,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
        request=request,
        actor_type='API'
    )
