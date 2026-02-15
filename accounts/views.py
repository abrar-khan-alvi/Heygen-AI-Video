"""
Views for accounts app.

This module contains all authentication endpoints:
- Sign Up, OTP Verification
- Login, Logout
- Password Reset, Change Password
- User Profile
- Google/Apple OAuth
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .models import CustomUser, PasswordResetToken, PendingRegistration
from .serializers import (
    SignUpSerializer,
    VerifyOTPSerializer,
    ResendOTPSerializer,
    LoginSerializer,
    ForgotPasswordSerializer,
    VerifyPasswordResetOTPSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    ProfileSerializer,
    GoogleAuthSerializer,
    AppleAuthSerializer,
)
from .utils import (
    send_password_reset_email,
    verify_password_reset_token,
)


def get_tokens_for_user(user):
    """
    Generate JWT tokens for a user.
    
    Returns both access and refresh tokens.
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def send_pending_otp_email(pending_registration):
    """
    Send OTP email for pending registration.
    """
    subject = '🔐 Verify Your Email - OTP Code'
    
    text_content = f"""
Hello {pending_registration.username},

Your OTP code for email verification is: {pending_registration.otp_code}

This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.

If you didn't request this, please ignore this email.

Best regards,
The Team
    """
    
    html_content = render_to_string('emails/otp_verification.html', {
        'username': pending_registration.username,
        'otp_code': pending_registration.otp_code,
        'expiry_minutes': settings.OTP_EXPIRY_MINUTES,
    })
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[pending_registration.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


# =============================================================================
# REGISTRATION & EMAIL VERIFICATION
# =============================================================================

class SignUpView(APIView):
    """
    Register a new user (stores in pending until OTP verified).
    
    POST /api/v1/auth/signup/
    
    Request body:
    {
        "username": "johndoe",
        "email": "john@example.com",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!"
    }
    
    Response:
    {
        "message": "Registration successful. Please check your email for OTP.",
        "email": "john@example.com"
    }
    
    Flow:
    1. Validate input data
    2. Store in PendingRegistration (NOT actual User table)
    3. Send OTP to email
    4. Return success message
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email'].lower()
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        # Check if email already exists in User table
        if CustomUser.objects.filter(email=email).exists():
            return Response(
                {'email': ['This email is already registered.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if username already exists in User table
        if CustomUser.objects.filter(username=username).exists():
            return Response(
                {'username': ['This username is already taken.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete any existing pending registration for this email
        PendingRegistration.objects.filter(email=email).delete()
        
        # Generate OTP
        otp_code = PendingRegistration.generate_otp()
        
        # Create pending registration (password stored hashed)
        pending = PendingRegistration.objects.create(
            email=email,
            username=username,
            password_hash=make_password(password),
            otp_code=otp_code
        )
        
        # Send OTP email
        try:
            send_pending_otp_email(pending)
        except Exception as e:
            pending.delete()
            return Response(
                {'error': 'Failed to send verification email. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': 'Registration successful. Please check your email for OTP.',
            'email': email
        }, status=status.HTTP_201_CREATED)


class VerifyOTPView(APIView):
    """
    Verify email with OTP and create the actual user account.
    
    POST /api/v1/auth/verify-otp/
    
    Request body:
    {
        "email": "john@example.com",
        "otp": "123456"
    }
    
    Response (success):
    {
        "message": "Email verified successfully! You can now login.",
        "verified": true
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email'].lower()
        otp_code = serializer.validated_data['otp']
        
        # Find pending registration
        try:
            pending = PendingRegistration.objects.get(email=email)
        except PendingRegistration.DoesNotExist:
            return Response(
                {'error': 'No pending registration found. Please sign up again.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if expired
        if pending.is_expired:
            pending.delete()
            return Response(
                {'error': 'OTP has expired. Please sign up again.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if max attempts reached
        if pending.is_max_attempts_reached:
            pending.delete()
            return Response(
                {'error': 'Maximum attempts reached. Please sign up again.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify OTP
        if pending.otp_code != otp_code:
            pending.attempts += 1
            pending.save()
            remaining = 3 - pending.attempts
            return Response(
                {'error': f'Invalid OTP. {remaining} attempts remaining.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # OTP is correct! Create the actual user
        try:
            user = CustomUser.objects.create(
                email=pending.email,
                username=pending.username,
                password=pending.password_hash,  # Already hashed
                is_email_verified=True,
                auth_provider=CustomUser.AuthProvider.EMAIL
            )
        except Exception as e:
            return Response(
                {'error': 'Failed to create account. Username or email may already be taken.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete pending registration
        pending.delete()
        
        return Response({
            'message': 'Email verified successfully! You can now login.',
            'verified': True
        }, status=status.HTTP_200_OK)


class ResendOTPView(APIView):
    """
    Resend OTP to email.
    
    POST /api/v1/auth/resend-otp/
    
    Request body:
    {
        "email": "john@example.com"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email'].lower()
        
        # Find pending registration
        try:
            pending = PendingRegistration.objects.get(email=email)
        except PendingRegistration.DoesNotExist:
            return Response(
                {'error': 'No pending registration found. Please sign up again.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate new OTP and reset attempts
        pending.otp_code = PendingRegistration.generate_otp()
        pending.attempts = 0
        pending.expires_at = None  # Will be reset on save
        pending.save()
        
        try:
            send_pending_otp_email(pending)
        except Exception:
            return Response(
                {'error': 'Failed to send OTP. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': 'OTP sent successfully. Please check your email.'
        }, status=status.HTTP_200_OK)


# =============================================================================
# LOGIN & LOGOUT
# =============================================================================

class LoginView(APIView):
    """
    Login with email/username and password.
    
    POST /api/v1/auth/login/
    
    Request body:
    {
        "email_or_username": "john@example.com",  // or "johndoe"
        "password": "SecurePass123!"
    }
    
    Response:
    {
        "message": "Login successful",
        "tokens": {
            "access": "eyJ...",
            "refresh": "eyJ..."
        },
        "user": {
            "id": "uuid",
            "username": "johndoe",
            "email": "john@example.com"
        }
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.validated_data['user']
        tokens = get_tokens_for_user(user)
        
        return Response({
            'message': 'Login successful',
            'tokens': tokens,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
            }
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    Logout user by blacklisting refresh token.
    
    POST /api/v1/auth/logout/
    
    Request body:
    {
        "refresh": "eyJ..."
    }
    
    Note: Requires authentication (access token in header)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
            
        except Exception:
            return Response(
                {'error': 'Invalid token.'},
                status=status.HTTP_400_BAD_REQUEST
            )


# =============================================================================
# PASSWORD MANAGEMENT
# =============================================================================

class ForgotPasswordView(APIView):
    """
    Request password reset email.
    
    POST /api/v1/auth/forgot-password/
    
    Request body:
    {
        "email": "john@example.com"
    }
    
    Note: Always returns success to prevent email enumeration
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        
        try:
            user = CustomUser.objects.get(email=email.lower())
            send_password_reset_email(user)
        except CustomUser.DoesNotExist:
            # Don't reveal if email exists (security)
            pass
        except Exception:
            # Email failed, but don't reveal
            pass
        
        # Always return success (security)
        return Response({
            'message': 'If an account exists with this email, a reset link has been sent.'
        }, status=status.HTTP_200_OK)


class VerifyPasswordResetOTPView(APIView):
    """
    Verify OTP for password reset.
    
    POST /api/v1/auth/verify-reset-otp/
    
    Request body:
    {
        "email": "john@example.com",
        "otp": "123456"
    }
    
    Response (success):
    {
        "message": "OTP verified successfully.",
        "token": "uuid-token"  // Use this token for the next step (Reset Password)
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = VerifyPasswordResetOTPSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email'].lower()
        otp = serializer.validated_data['otp']
        
        try:
            user = CustomUser.objects.get(email=email)
            reset_token = PasswordResetToken.objects.get(user=user)
        except (CustomUser.DoesNotExist, PasswordResetToken.DoesNotExist):
            return Response(
                {'error': 'Invalid request or expired session.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if reset_token.is_expired:
            reset_token.delete()
            return Response(
                {'error': 'OTP has expired. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if reset_token.otp_code != otp:
            return Response(
                {'error': 'Invalid OTP.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        return Response({
            'message': 'OTP verified successfully.',
            'token': reset_token.token
        }, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    """
    Reset password using token from email.
    
    POST /api/v1/auth/reset-password/
    
    Request body:
    {
        "token": "uuid-token",
        "password": "NewPass123!",
        "password_confirm": "NewPass123!"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']
        
        # Verify token
        user, message = verify_password_reset_token(token)
        
        if not user:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update password
        user.set_password(password)
        user.save()
        
        # Delete token
        PasswordResetToken.objects.filter(user=user).delete()
        
        return Response({
            'message': 'Password reset successful. You can now login.'
        }, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """
    Change password for authenticated user.
    
    POST /api/v1/auth/change-password/
    
    Request body:
    {
        "old_password": "OldPass123!",
        "new_password": "NewPass123!",
        "new_password_confirm": "NewPass123!"
    }
    
    Requires: Authentication
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        # Verify old password
        if not user.check_password(old_password):
            return Response(
                {'error': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update password
        user.set_password(new_password)
        user.save()
        
        return Response({
            'message': 'Password changed successfully.'
        }, status=status.HTTP_200_OK)


# =============================================================================
# USER PROFILE
# =============================================================================

class ProfileView(APIView):
    """
    View and update user profile.
    
    GET /api/v1/auth/profile/
    Returns user profile data.
    
    PATCH /api/v1/auth/profile/
    Update username.
    
    Requires: Authentication
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        serializer = ProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


# =============================================================================
# SOCIAL AUTHENTICATION
# =============================================================================

class GoogleAuthView(APIView):
    """
    Login/Register with Google.
    
    POST /api/v1/auth/google/
    
    Request body:
    {
        "token": "google-id-token"
    }
    
    Flow:
    1. Verify token with Google
    2. If user exists with this Google ID, login
    3. If email exists but no Google ID, link accounts
    4. If new user, create account
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        token = serializer.validated_data['token']
        
        try:
            # Verify token with Google
            from google.oauth2 import id_token
            from google.auth.transport import requests
            
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID if hasattr(settings, 'GOOGLE_CLIENT_ID') else None
            )
            
            google_id = idinfo['sub']
            email = idinfo['email']
            name = idinfo.get('name', email.split('@')[0])
            
        except ValueError as e:
            return Response(
                {'error': 'Invalid Google token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Google authentication failed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists with this Google ID
        user = CustomUser.objects.filter(google_id=google_id).first()
        
        if not user:
            # Check if email exists
            user = CustomUser.objects.filter(email=email.lower()).first()
            
            if user:
                # Link Google ID to existing account
                user.google_id = google_id
                if not user.is_email_verified:
                    user.is_email_verified = True  # Google verified their email
                user.save()
            else:
                # Create new user
                username = self._generate_unique_username(name)
                user = CustomUser.objects.create_user(
                    email=email.lower(),
                    username=username,
                    password=None,  # No password for social auth
                    is_email_verified=True,
                    auth_provider=CustomUser.AuthProvider.GOOGLE,
                    google_id=google_id
                )
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        
        return Response({
            'message': 'Google authentication successful',
            'tokens': tokens,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
            }
        }, status=status.HTTP_200_OK)
    
    def _generate_unique_username(self, name):
        """Generate a unique username from name."""
        import re
        import random
        
        # Clean name
        base = re.sub(r'[^a-z0-9]', '', name.lower())[:20]
        if not base:
            base = 'user'
        
        username = base
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base}{random.randint(1000, 9999)}"
        
        return username


class AppleAuthView(APIView):
    """
    Login/Register with Apple.
    
    POST /api/v1/auth/apple/
    
    Request body:
    {
        "token": "apple-id-token",
        "user_info": {  // Only sent on first login
            "name": "John Doe",
            "email": "john@privaterelay.appleid.com"
        }
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = AppleAuthSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        token = serializer.validated_data['token']
        user_info = serializer.validated_data.get('user_info', {})
        
        try:
            import jwt
            
            # Decode token (Apple uses RS256, but for simplicity we'll decode without verification)
            # In production, you should verify with Apple's public keys
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            apple_id = decoded['sub']
            email = decoded.get('email') or user_info.get('email')
            
            if not email:
                return Response(
                    {'error': 'Email is required for Apple Sign In.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        except Exception as e:
            return Response(
                {'error': 'Invalid Apple token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists with this Apple ID
        user = CustomUser.objects.filter(apple_id=apple_id).first()
        
        if not user:
            # Check if email exists
            user = CustomUser.objects.filter(email=email.lower()).first()
            
            if user:
                # Link Apple ID to existing account
                user.apple_id = apple_id
                if not user.is_email_verified:
                    user.is_email_verified = True
                user.save()
            else:
                # Create new user
                name = user_info.get('name', email.split('@')[0])
                username = self._generate_unique_username(name)
                user = CustomUser.objects.create_user(
                    email=email.lower(),
                    username=username,
                    password=None,
                    is_email_verified=True,
                    auth_provider=CustomUser.AuthProvider.APPLE,
                    apple_id=apple_id
                )
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        
        return Response({
            'message': 'Apple authentication successful',
            'tokens': tokens,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
            }
        }, status=status.HTTP_200_OK)
    
    def _generate_unique_username(self, name):
        """Generate a unique username from name."""
        import re
        import random
        
        base = re.sub(r'[^a-z0-9]', '', name.lower())[:20]
        if not base:
            base = 'user'
        
        username = base
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base}{random.randint(1000, 9999)}"
        
        return username

