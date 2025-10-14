"""
URL configuration for common app file management.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FileManagementViewSet, DocumentVersionManagementViewSet

# Create router for ViewSets
router = DefaultRouter()
router.register(r'files', FileManagementViewSet, basename='file-management')
router.register(r'versions', DocumentVersionManagementViewSet, basename='document-versions')

urlpatterns = [
    path('', include(router.urls)),
]