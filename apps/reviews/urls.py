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
    # Phase 4.3 ViewSets
    DecisionLetterTemplateViewSet,
    EditorialDecisionViewSet,
    RevisionRoundViewSet,
)

app_name = 'reviews'

router = DefaultRouter()

# Phase 4.1 & 4.2 Routes
router.register(r'assignments', ReviewAssignmentViewSet, basename='assignment')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'recommendations', ReviewerRecommendationViewSet, basename='recommendation')
router.register(r'search', ReviewerSearchViewSet, basename='search')
router.register(r'statistics', ReviewStatisticsViewSet, basename='statistics')
router.register(r'forms', ReviewFormTemplateViewSet, basename='form')

# Phase 4.3 Routes - Editorial Decision Making
router.register(r'decision-templates', DecisionLetterTemplateViewSet, basename='decision-template')
router.register(r'decisions', EditorialDecisionViewSet, basename='decision')
router.register(r'revisions', RevisionRoundViewSet, basename='revision')

urlpatterns = [
    path('', include(router.urls)),
]