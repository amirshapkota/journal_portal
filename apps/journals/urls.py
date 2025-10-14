"""
URL configuration for journals app.
Handles journal models and settings.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JournalViewSet

router = DefaultRouter()
router.register(r'', JournalViewSet, basename='journal')

app_name = 'journals'

urlpatterns = [
    path('', include(router.urls)),
]