"""
URL configuration for integrations app.
Handles ORCID/OJS connectors and external services.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# from .views import ORCIDViewSet, OJSViewSet, ExternalServiceViewSet

router = DefaultRouter()
# router.register(r'orcid', ORCIDViewSet)
# router.register(r'ojs', OJSViewSet)
# router.register(r'services', ExternalServiceViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Add custom integration endpoints here
    # path('orcid/connect/', ORCIDConnectView.as_view(), name='orcid_connect'),
    # path('orcid/sync/', ORCIDSyncView.as_view(), name='orcid_sync'),
    # path('ojs/sync/', OJSSyncView.as_view(), name='ojs_sync'),
    # path('ojs/export/', OJSExportView.as_view(), name='ojs_export'),
    # path('ror/search/', RORSearchView.as_view(), name='ror_search'),
    # path('openalex/search/', OpenAlexSearchView.as_view(), name='openalex_search'),
]