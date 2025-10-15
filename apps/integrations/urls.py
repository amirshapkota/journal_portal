"""
URL configuration for integrations app.
Handles ORCID/OJS connectors and external services.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ORCIDAuthorizeView,
    ORCIDCallbackView,
    ORCIDStatusView,
    ORCIDDisconnectView,
    ORCIDSyncProfileView,
)

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    # ORCID OAuth flow
    path('orcid/authorize/', ORCIDAuthorizeView.as_view(), name='orcid_authorize'),
    path('orcid/callback/', ORCIDCallbackView.as_view(), name='orcid_callback'),
    path('orcid/status/', ORCIDStatusView.as_view(), name='orcid_status'),
    path('orcid/disconnect/', ORCIDDisconnectView.as_view(), name='orcid_disconnect'),
    path('orcid/sync-profile/', ORCIDSyncProfileView.as_view(), name='orcid_sync_profile'),
]