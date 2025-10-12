"""
URL configuration for precheck app.
Handles plagiarism and formatting checks.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# from .views import PrecheckViewSet, PlagiarismCheckViewSet, FormatCheckViewSet

router = DefaultRouter()
# router.register(r'prechecks', PrecheckViewSet)
# router.register(r'plagiarism', PlagiarismCheckViewSet)
# router.register(r'format', FormatCheckViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Add custom precheck endpoints here
    # path('plagiarism/check/', PlagiarismCheckView.as_view(), name='plagiarism_check'),
    # path('format/validate/', FormatValidationView.as_view(), name='format_validation'),
    # path('requirements/check/', RequirementsCheckView.as_view(), name='requirements_check'),
]