"""
API views for email notifications and preferences.
"""
from rest_framework import viewsets, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta

from apps.notifications.models import EmailNotificationPreference, EmailLog
from apps.notifications.serializers import (
    EmailNotificationPreferenceSerializer,
    EmailLogSerializer
)


class EmailPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing email notification preferences.
    
    Endpoints:
    - GET /api/v1/notifications/email-preferences/ - Get current user's preferences
    - POST /api/v1/notifications/email-preferences/update_preferences/ - Update preferences
    - POST /api/v1/notifications/email-preferences/{id}/toggle_all/ - Enable/disable all notifications
    """
    
    serializer_class = EmailNotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__email']
    filterset_fields = ['user']
    ordering_fields = ['id']
    ordering = ['id']
    
    def get_queryset(self):
        """Return only current user's preferences."""
        return EmailNotificationPreference.objects.filter(user=self.request.user)
    
    def list(self, request):
        """List preferences for current user with pagination/filtering."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def update_preferences(self, request):
        """Update preferences."""
        preference, created = EmailNotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = EmailNotificationPreferenceSerializer(
            preference, 
            data=request.data, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_all(self, request, pk=None):
        """
        Enable or disable all email notifications.
        
        Body: {"enabled": true/false}
        """
        preference = self.get_object()
        enabled = request.data.get('enabled', True)
        
        preference.email_notifications_enabled = enabled
        preference.save()
        
        serializer = self.get_serializer(preference)
        return Response({
            'message': f'Email notifications {"enabled" if enabled else "disabled"}',
            'email_notifications_enabled': preference.email_notifications_enabled,
            'preferences': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def enable_all(self, request):
        """Enable all notification types."""
        preference, created = EmailNotificationPreference.objects.get_or_create(
            user=request.user
        )
        
        # Enable all boolean fields
        for field in preference._meta.fields:
            if field.get_internal_type() == 'BooleanField' and field.name != 'id':
                setattr(preference, field.name, True)
        
        preference.save()
        
        serializer = self.get_serializer(preference)
        return Response({
            'message': 'All email notifications enabled',
            'preferences': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def disable_all(self, request):
        """Disable all notification types."""
        preference, created = EmailNotificationPreference.objects.get_or_create(
            user=request.user
        )
        
        # Disable all boolean fields
        for field in preference._meta.fields:
            if field.get_internal_type() == 'BooleanField' and field.name != 'id':
                setattr(preference, field.name, False)
        
        preference.save()
        
        serializer = self.get_serializer(preference)
        return Response({
            'message': 'All email notifications disabled',
            'preferences': serializer.data
        })


class EmailLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing email logs.
    
    Endpoints:
    - GET /api/v1/notifications/email-logs/ - List emails sent to current user
    - GET /api/v1/notifications/email-logs/{id}/ - Get specific email log
    - GET /api/v1/notifications/email-logs/stats/ - Get email statistics
    - GET /api/v1/notifications/email-logs/user_stats/ - Get user-specific statistics
    """
    
    serializer_class = EmailLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['subject', 'to_email']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return email logs for current user only."""
        return EmailLog.objects.filter(
            user=self.request.user
        ).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get emails from last 30 days."""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        logs = self.get_queryset().filter(created_at__gte=thirty_days_ago)
        
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def failed(self, request):
        """Get failed email deliveries."""
        logs = self.get_queryset().filter(status='FAILED')
        
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get global email statistics."""
        # Get all email logs (not filtered by user)
        all_logs = EmailLog.objects.all()
        
        total = all_logs.count()
        sent = all_logs.filter(status='SENT').count()
        pending = all_logs.filter(status='PENDING').count()
        failed = all_logs.filter(status='FAILED').count()
        
        # Calculate success rate
        success_rate = (sent / total * 100) if total > 0 else 0
        
        # Stats by template type
        from django.db.models import Count
        by_template = dict(
            all_logs.values_list('template_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        return Response({
            'total': total,
            'sent': sent,
            'pending': pending,
            'failed': failed,
            'success_rate': round(success_rate, 2),
            'by_template_type': by_template,
        })
    
    @action(detail=False, methods=['get'])
    def user_stats(self, request):
        """Get email statistics for current user, with pagination and filtering."""
        queryset = self.filter_queryset(self.get_queryset())

        total = queryset.count()
        sent = queryset.filter(status='SENT').count()
        pending = queryset.filter(status='PENDING').count()
        failed = queryset.filter(status='FAILED').count()

        # Recent emails (last 7 days, paginated)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_emails_qs = queryset.filter(created_at__gte=seven_days_ago)
        page = self.paginate_queryset(recent_emails_qs)
        if page is not None:
            recent_emails = self.get_serializer(page, many=True).data
        else:
            recent_emails = self.get_serializer(recent_emails_qs, many=True).data

        # Custom paginated response: stats + paginated recent_emails
        paginated = self.get_paginated_response(recent_emails)
        paginated.data.update({
            'total': total,
            'sent': sent,
            'pending': pending,
            'failed': failed,
        })
        return paginated
