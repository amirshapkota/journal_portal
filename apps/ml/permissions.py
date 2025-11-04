"""
Custom permissions for ML features.
"""
from rest_framework import permissions


class IsAdminOrEditor(permissions.BasePermission):
    """
    Permission that allows access only to admin users or editors.
    
    For anomaly detection: Only admins/editors should see security issues.
    For reviewer recommendations: Any authenticated user can access.
    """
    
    message = "You must be an admin or editor to access this resource."
    
    def has_permission(self, request, view):
        """Check if user is admin or has editor role."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers always have access
        if request.user.is_superuser:
            return True
        
        # Staff users have access
        if request.user.is_staff:
            return True
        
        # Check if user has 'editor' role
        try:
            if hasattr(request.user, 'profile') and request.user.profile:
                profile = request.user.profile
                if hasattr(profile, 'role') and profile.role in ['editor', 'admin', 'chief_editor']:
                    return True
        except Exception:
            # If profile doesn't exist or there's an error, deny access
            pass
        
        return False


class IsAdminOnly(permissions.BasePermission):
    """
    Permission that allows access only to admin users.
    
    For highly sensitive operations like comprehensive anomaly scans.
    """
    
    message = "You must be an administrator to access this resource."
    
    def has_permission(self, request, view):
        """Check if user is admin."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers only
        if request.user.is_superuser:
            return True
        
        # Or users with admin role
        if hasattr(request.user, 'profile'):
            if request.user.profile.role == 'admin':
                return True
        
        return False


class CanViewOwnRiskScore(permissions.BasePermission):
    """
    Permission for users to view their own risk score.
    
    Users can check their own anomaly status, but only admins can see others.
    """
    
    def has_permission(self, request, view):
        """Check if user can access risk scores."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admins can view anyone's risk score
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Get the user_id from URL parameters
        user_id = view.kwargs.get('user_id')
        
        # Users can view their own risk score
        try:
            if hasattr(request.user, 'profile') and request.user.profile:
                if str(request.user.profile.id) == str(user_id):
                    return True
        except Exception:
            # If profile doesn't exist or there's an error, deny access
            pass
        
        return False
