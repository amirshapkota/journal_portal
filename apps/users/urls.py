"""
URL configuration for users app.

Defines routes for authentication, user management, and profile operations
with JWT token handling and comprehensive user account functionality.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import verification_views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'profiles', views.ProfileViewSet)
router.register(r'roles', views.RoleViewSet)
router.register(r'verification-requests', verification_views.VerificationRequestViewSet, basename='verification-request')
router.register(r'admin/verifications', verification_views.AdminVerificationViewSet, basename='admin-verification')

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    
    # Registration and verification
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    path('auth/verify-email/', views.EmailVerificationView.as_view(), name='verify_email'),
    
    # Password management
    path('auth/password/change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('auth/password/reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password/reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # User information
    path('auth/me/', views.current_user, name='current_user'),
    
    # Health check
    path('health/', views.health_check, name='health_check'),
    
    # Verification status
    path('verification/status/', verification_views.VerificationStatusView.as_view(), name='verification_status'),
    
    # Include router URLs
    path('', include(router.urls)),
]