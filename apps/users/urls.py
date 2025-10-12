"""
URL configuration for users app.
Handles authentication, user profiles, and verification.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# from .views import UserViewSet, ProfileViewSet

router = DefaultRouter()
# router.register(r'users', UserViewSet)
# router.register(r'profiles', ProfileViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Add custom auth endpoints here
    # path('login/', LoginView.as_view(), name='login'),
    # path('logout/', LogoutView.as_view(), name='logout'),
    # path('register/', RegisterView.as_view(), name='register'),
    # path('verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    # path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
]