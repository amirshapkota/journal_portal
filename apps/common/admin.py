from django.contrib import admin
from .models import ActivityLog, VerificationTicket, Concept, Embedding, AnomalyEvent, Award


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """Admin interface for ActivityLog model."""
    list_display = ['user', 'action_type', 'resource_type', 'resource_id', 'actor_type', 'created_at']
    list_filter = ['action_type', 'resource_type', 'actor_type', 'created_at']
    search_fields = ['user__email', 'resource_id', 'ip_address', 'metadata']
    readonly_fields = [
        'id', 'user', 'actor_type', 'action_type', 'resource_type', 
        'resource_id', 'metadata', 'ip_address', 'user_agent', 
        'session_id', 'created_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Prevent adding logs manually."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion only for superusers."""
        return request.user.is_superuser

