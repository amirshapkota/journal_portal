"""
URL configuration for journal_portal project.

A modern, secure, auditable Journal Publication Portal.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API endpoints
    path('api/v1/', include('users.urls')),
    path('api/v1/journals/', include('journals.urls')),
    path('api/v1/submissions/', include('submissions.urls')),
    path('api/v1/reviews/', include('reviews.urls')),
    path('api/v1/precheck/', include('precheck.urls')),
    path('api/v1/integrations/', include('integrations.urls')),
    path('api/v1/ml/', include('ml.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
    
    # DRF Browsable API (in development)
    path('api-auth/', include('rest_framework.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
