from django.urls import path
from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    UserListCreateView,
    UserDetailView,
    LogoutView,
    PasswordChangeView,
    PasswordResetRequestView,
    PasswordResetConfirmView
)

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    
    # User management (admin only)
    path('users/', UserListCreateView.as_view(), name='user_list'),
      # User profile and management
    path('auth/user/', UserDetailView.as_view(), name='user_details'),
    path('auth/user/<int:pk>/', UserDetailView.as_view(), name='user_detail_actions'),
    
    # Password management
    path('auth/password-change/', PasswordChangeView.as_view(), name='password_change'),
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]