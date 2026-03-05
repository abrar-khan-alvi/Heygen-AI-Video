"""
URL Configuration for accounts app.

All URLs here are prefixed with /api/v1/auth/
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [

    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend-otp'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-reset-otp/', views.VerifyPasswordResetOTPView.as_view(), name='verify-reset-otp'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('google/', views.GoogleAuthView.as_view(), name='google-auth'),
    path('apple/', views.AppleAuthView.as_view(), name='apple-auth'),
    
]
