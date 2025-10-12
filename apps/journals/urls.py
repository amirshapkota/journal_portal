"""
URL configuration for journals app.
Handles journal models and settings.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# from .views import JournalViewSet, JournalSettingsViewSet

router = DefaultRouter()
# router.register(r'journals', JournalViewSet)
# router.register(r'settings', JournalSettingsViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Add custom journal endpoints here
    # path('<int:journal_id>/settings/', JournalSettingsView.as_view(), name='journal_settings'),
    # path('<int:journal_id>/staff/', JournalStaffView.as_view(), name='journal_staff'),
]