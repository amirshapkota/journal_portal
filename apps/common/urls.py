"""
URL configuration for common app file management.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FileManagementViewSet, 
    DocumentVersionManagementViewSet, 
    ActivityLogViewSet,
    PublicPublicationViewSet
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'files', FileManagementViewSet, basename='file-management')
router.register(r'versions', DocumentVersionManagementViewSet, basename='document-versions')
router.register(r'activity-logs', ActivityLogViewSet, basename='activity-logs')

# Public endpoints (no authentication required)
router.register(r'publications', PublicPublicationViewSet, basename='public-publications')

urlpatterns = [
    path('', include(router.urls)),
]