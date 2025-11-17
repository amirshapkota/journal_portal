"""
URL configuration for journals app.
Handles journal models and settings.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    JournalViewSet, SectionViewSet, CategoryViewSet,
    ResearchTypeViewSet, AreaViewSet
)

router = DefaultRouter()
router.register(r'journals', JournalViewSet, basename='journal')
router.register(r'sections', SectionViewSet, basename='section')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'research-types', ResearchTypeViewSet, basename='research-type')
router.register(r'areas', AreaViewSet, basename='area')

app_name = 'journals'

urlpatterns = [
    path('', include(router.urls)),
]