"""
URL configuration for reviews app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.reviews.views import (
    ReviewAssignmentViewSet,
    ReviewViewSet,
    ReviewerRecommendationViewSet,
    ReviewerSearchViewSet,
    ReviewStatisticsViewSet,
    ReviewFormTemplateViewSet,
)

app_name = 'reviews'

router = DefaultRouter()
router.register(r'assignments', ReviewAssignmentViewSet, basename='assignment')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'recommendations', ReviewerRecommendationViewSet, basename='recommendation')
router.register(r'search', ReviewerSearchViewSet, basename='search')
router.register(r'statistics', ReviewStatisticsViewSet, basename='statistics')
router.register(r'forms', ReviewFormTemplateViewSet, basename='form')

urlpatterns = [
    path('', include(router.urls)),
]