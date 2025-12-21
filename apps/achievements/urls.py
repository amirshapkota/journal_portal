"""
URL configuration for achievements app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    BadgeViewSet, UserBadgeViewSet, AwardViewSet,
    LeaderboardViewSet, CertificateViewSet
)

app_name = 'achievements'

router = DefaultRouter()
router.register(r'badges', BadgeViewSet, basename='badge')
router.register(r'user-badges', UserBadgeViewSet, basename='userbadge')
router.register(r'awards', AwardViewSet, basename='award')
router.register(r'leaderboards', LeaderboardViewSet, basename='leaderboard')
router.register(r'certificates', CertificateViewSet, basename='certificate')

urlpatterns = [
    path('', include(router.urls)),
]
