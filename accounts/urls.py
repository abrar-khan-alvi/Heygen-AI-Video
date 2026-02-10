"""
URL Configuration for accounts app.

All URLs here are prefixed with /api/v1/auth/
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # ==========================================================================
    # REGISTRATION & EMAIL VERIFICATION
    # ==========================================================================
    
    # POST /api/v1/auth/signup/
    # Register a new user, sends OTP to email
    path('signup/', views.SignUpView.as_view(), name='signup'),
    
    # POST /api/v1/auth/verify-otp/
    # Verify OTP to confirm email
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    
    # POST /api/v1/auth/resend-otp/
    # Resend OTP to email
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend-otp'),
    
    # ==========================================================================
    # LOGIN & LOGOUT
    # ==========================================================================
    
    # POST /api/v1/auth/login/
    # Login with email/username and password
    path('login/', views.LoginView.as_view(), name='login'),
    
    # POST /api/v1/auth/logout/
    # Logout (blacklist refresh token)
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # POST /api/v1/auth/token/refresh/
    # Get new access token using refresh token
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # ==========================================================================
    # PASSWORD MANAGEMENT
    # ==========================================================================
    
    # POST /api/v1/auth/forgot-password/
    # Request password reset email (sends OTP)
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    
    # POST /api/v1/auth/verify-reset-otp/
    # Verify OTP and get reset token
    path('verify-reset-otp/', views.VerifyPasswordResetOTPView.as_view(), name='verify-reset-otp'),
    
    # POST /api/v1/auth/reset-password/
    # Reset password using token
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),
    
    # POST /api/v1/auth/change-password/
    # Change password (authenticated users)
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    
    # ==========================================================================
    # USER PROFILE
    # ==========================================================================
    
    # GET, PATCH /api/v1/auth/profile/
    # View or update user profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    # ==========================================================================
    # SOCIAL AUTHENTICATION
    # ==========================================================================
    
    # POST /api/v1/auth/google/
    # Login/register with Google
    path('google/', views.GoogleAuthView.as_view(), name='google-auth'),
    
    # POST /api/v1/auth/apple/
    # Login/register with Apple
    path('apple/', views.AppleAuthView.as_view(), name='apple-auth'),
]
