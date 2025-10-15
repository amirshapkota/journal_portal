"""
URL configuration for notifications app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.notifications.views import EmailPreferenceViewSet, EmailLogViewSet

router = DefaultRouter()
router.register(r'email-preferences', EmailPreferenceViewSet, basename='email-preferences')
router.register(r'email-logs', EmailLogViewSet, basename='email-logs')

app_name = 'notifications'

urlpatterns = [
    path('', include(router.urls)),
]
