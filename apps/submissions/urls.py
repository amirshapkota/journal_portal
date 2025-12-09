"""
URL configuration for submissions app.
Handles submissions, documents, versions, copyediting, and production workflows.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubmissionViewSet
from .superdoc_views import SuperDocViewSet
from .workflow_views import (
    CopyeditingAssignmentViewSet,
    CopyeditingFileViewSet,
    CopyeditingDiscussionViewSet,
    ProductionAssignmentViewSet,
    ProductionFileViewSet,
    ProductionDiscussionViewSet,
    PublicationScheduleViewSet,
)

router = DefaultRouter()
router.register(r'', SubmissionViewSet, basename='submission')
router.register(r'documents', SuperDocViewSet, basename='superdoc')

# Copyediting workflow routes
router.register(r'copyediting/assignments', CopyeditingAssignmentViewSet, basename='copyediting-assignment')
router.register(r'copyediting/files', CopyeditingFileViewSet, basename='copyediting-file')
router.register(r'copyediting/discussions', CopyeditingDiscussionViewSet, basename='copyediting-discussion')

# Production workflow routes
router.register(r'production/assignments', ProductionAssignmentViewSet, basename='production-assignment')
router.register(r'production/files', ProductionFileViewSet, basename='production-file')
router.register(r'production/discussions', ProductionDiscussionViewSet, basename='production-discussion')
router.register(r'production/schedules', PublicationScheduleViewSet, basename='publication-schedule')

app_name = 'submissions'

urlpatterns = [
    path('', include(router.urls)),
]