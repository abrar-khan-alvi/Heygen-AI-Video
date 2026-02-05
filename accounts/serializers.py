"""
Serializers for accounts app.

Serializers convert complex data types (like Django models) to Python 
datatypes that can be rendered into JSON. They also handle validation.

Each serializer has:
- Input validation
- Output formatting
- Helpful error messages
"""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from .models import CustomUser


class SignUpSerializer(serializers.Serializer):
    """
    Serializer for user registration.
    
    Required fields:
    - username: Unique username (3-30 chars)
    - email: Valid, unique email
    - password: Strong password
    - password_confirm: Must match password
    
    Note: This is a regular Serializer, not a ModelSerializer,
    because we want more control over the creation process.
    """
    
    username = serializers.CharField(
        min_length=3,
        max_length=30,
        help_text="Username must be 3-30 characters"
    )
    
    email = serializers.EmailField(
        help_text="Valid email address"
    )
    
    password = serializers.CharField(
        write_only=True,  # Never include in response
        min_length=8,
        help_text="Password must be at least 8 characters"
    )
    
    password_confirm = serializers.CharField(
        write_only=True,
        help_text="Must match password"
    )
    
    def validate_username(self, value):
        """Check username is unique."""
        if CustomUser.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value.lower()  # Normalize to lowercase
    
    def validate_email(self, value):
        """Check email is unique."""
        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value.lower()  # Normalize to lowercase
    
    def validate_password(self, value):
        """Validate password strength using Django's validators."""
        validate_password(value)
        return value
    
    def validate(self, data):
        """Check passwords match."""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Passwords do not match."
            })
        return data
    
    def create(self, validated_data):
        """Create new user."""
        validated_data.pop('password_confirm')  # Remove before creating
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user


class VerifyOTPSerializer(serializers.Serializer):
    """
    Serializer for OTP verification.
    
    Required fields:
    - email: User's email
    - otp: 6-digit OTP code
    """
    
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)
    
    def validate_otp(self, value):
        """Ensure OTP is numeric."""
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be 6 digits.")
        return value


class ResendOTPSerializer(serializers.Serializer):
    """Serializer for resending OTP."""
    
    email = serializers.EmailField()


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    
    Supports login with:
    - email + password
    - username + password
    
    The 'email_or_username' field accepts either.
    """
    
    email_or_username = serializers.CharField(
        help_text="Email address or username"
    )
    
    password = serializers.CharField(
        write_only=True
    )
    
    def validate(self, data):
        """
        Authenticate user with email or username.
        
        Returns the authenticated user in validated_data.
        """
        email_or_username = data['email_or_username'].lower()
        password = data['password']
        
        # Try to find user by email or username
        try:
            if '@' in email_or_username:
                user = CustomUser.objects.get(email=email_or_username)
            else:
                user = CustomUser.objects.get(username=email_or_username)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({
                'email_or_username': "No account found with this email/username."
            })
        
        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError({
                'password': "Incorrect password."
            })
        
        # Check if account is active
        if not user.is_active:
            raise serializers.ValidationError({
                'email_or_username': "This account is disabled."
            })
        
        # Check if email is verified
        if not user.is_email_verified:
            raise serializers.ValidationError({
                'email_or_username': "Please verify your email before logging in."
            })
        
        data['user'] = user
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    """
    Serializer for password reset.
    
    Required fields:
    - token: Reset token from email
    - password: New password
    - password_confirm: Must match password
    """
    
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    def validate_password(self, value):
        """Validate password strength."""
        validate_password(value)
        return value
    
    def validate(self, data):
        """Check passwords match."""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Passwords do not match."
            })
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing password (authenticated users).
    
    Required fields:
    - old_password: Current password
    - new_password: New password
    - new_password_confirm: Must match new_password
    """
    
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_new_password(self, value):
        """Validate password strength."""
        validate_password(value)
        return value
    
    def validate(self, data):
        """Check new passwords match."""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Passwords do not match."
            })
        return data


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile.
    
    Read-only fields:
    - id, email, auth_provider, is_email_verified, date_joined
    
    Editable fields:
    - username
    """
    
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'email',
            'auth_provider',
            'is_email_verified',
            'date_joined'
        ]
        read_only_fields = [
            'id',
            'email',
            'auth_provider',
            'is_email_verified',
            'date_joined'
        ]
    
    def validate_username(self, value):
        """Check username is unique (excluding current user)."""
        user = self.context['request'].user
        if CustomUser.objects.filter(username__iexact=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("Username already taken.")
        return value.lower()


class GoogleAuthSerializer(serializers.Serializer):
    """Serializer for Google OAuth."""
    
    token = serializers.CharField(
        help_text="Google ID token from frontend"
    )


class AppleAuthSerializer(serializers.Serializer):
    """Serializer for Apple OAuth."""
    
    token = serializers.CharField(
        help_text="Apple ID token from frontend"
    )
    
    # Apple sends user info only on first login
    user_info = serializers.DictField(
        required=False,
        help_text="User info from Apple (first login only)"
    )
