"""
URL configuration for ml app.
Handles ML integration points and jobs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# from .views import MLJobViewSet, EmbeddingViewSet, RecommendationViewSet

router = DefaultRouter()
# router.register(r'jobs', MLJobViewSet)
# router.register(r'embeddings', EmbeddingViewSet)
# router.register(r'recommendations', RecommendationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Add custom ML endpoints here
    # path('reviewer-recommendations/', ReviewerRecommendationView.as_view(), name='reviewer_recommendations'),
    # path('anomaly-detection/', AnomalyDetectionView.as_view(), name='anomaly_detection'),
    # path('text-analysis/', TextAnalysisView.as_view(), name='text_analysis'),
    # path('similarity-check/', SimilarityCheckView.as_view(), name='similarity_check'),
]