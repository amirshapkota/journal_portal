"""
URL configuration for ml app.
Handles ML integration points and ML-powered features.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ReviewerRecommendationView, ReviewerRecommendationCustomWeightsView

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    
    # Reviewer Recommendation endpoints
    path(
        'reviewer-recommendations/<uuid:submission_id>/',
        ReviewerRecommendationView.as_view(),
        name='reviewer_recommendations'
    ),
    path(
        'reviewer-recommendations/<uuid:submission_id>/custom-weights/',
        ReviewerRecommendationCustomWeightsView.as_view(),
        name='reviewer_recommendations_custom_weights'
    ),
    
    # Future ML endpoints
    # path('anomaly-detection/', AnomalyDetectionView.as_view(), name='anomaly_detection'),
    # path('text-analysis/', TextAnalysisView.as_view(), name='text_analysis'),
    # path('plagiarism-check/', PlagiarismCheckView.as_view(), name='plagiarism_check'),
]