"""
URL configuration for ml app.
Handles ML integration points and ML-powered features.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ReviewerRecommendationView,
    ReviewerRecommendationCustomWeightsView,
    AnomalyDetectionScanView,
    UserRiskScoreView,
    SubmissionAnomaliesView,
    ReviewerAnomaliesView,
)

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
    
    # Anomaly Detection endpoints
    path(
        'anomaly-detection/scan/',
        AnomalyDetectionScanView.as_view(),
        name='anomaly_detection_scan'
    ),
    path(
        'anomaly-detection/user/<uuid:user_id>/',
        UserRiskScoreView.as_view(),
        name='user_risk_score'
    ),
    path(
        'anomaly-detection/submission/<uuid:submission_id>/',
        SubmissionAnomaliesView.as_view(),
        name='submission_anomalies'
    ),
    path(
        'anomaly-detection/reviewer/<uuid:reviewer_id>/',
        ReviewerAnomaliesView.as_view(),
        name='reviewer_anomalies'
    ),
    
    # Future ML endpoints
    # path('text-analysis/', TextAnalysisView.as_view(), name='text_analysis'),
    # path('plagiarism-check/', PlagiarismCheckView.as_view(), name='plagiarism_check'),
]