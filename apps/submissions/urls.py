"""
URL configuration for submissions app.
Handles submissions, documents, and versions.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubmissionViewSet
from .superdoc_views import SuperDocViewSet

router = DefaultRouter()
router.register(r'', SubmissionViewSet, basename='submission')
router.register(r'documents', SuperDocViewSet, basename='superdoc')

app_name = 'submissions'

urlpatterns = [
    path('', include(router.urls)),
]