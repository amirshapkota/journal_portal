"""
URL configuration for reviews app.
Handles review management and assignments.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# from .views import ReviewViewSet, ReviewAssignmentViewSet, ReviewerViewSet

router = DefaultRouter()
# router.register(r'reviews', ReviewViewSet)
# router.register(r'assignments', ReviewAssignmentViewSet)
# router.register(r'reviewers', ReviewerViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Add custom review endpoints here
    # path('<int:submission_id>/assign/', AssignReviewerView.as_view(), name='assign_reviewer'),
    # path('<int:review_id>/decision/', ReviewDecisionView.as_view(), name='review_decision'),
    # path('recommendations/', ReviewerRecommendationsView.as_view(), name='reviewer_recommendations'),
]