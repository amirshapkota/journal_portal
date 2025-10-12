"""
URL configuration for submissions app.
Handles submissions, documents, and versions.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# from .views import SubmissionViewSet, DocumentViewSet, VersionViewSet

router = DefaultRouter()
# router.register(r'submissions', SubmissionViewSet)
# router.register(r'documents', DocumentViewSet)
# router.register(r'versions', VersionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Add custom submission endpoints here
    # path('<int:submission_id>/documents/', SubmissionDocumentsView.as_view(), name='submission_documents'),
    # path('<int:submission_id>/versions/', SubmissionVersionsView.as_view(), name='submission_versions'),
    # path('<int:submission_id>/status/', SubmissionStatusView.as_view(), name='submission_status'),
]