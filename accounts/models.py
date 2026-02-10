"""
Custom User Model and Authentication-related Models

Models:
1. CustomUser - Main user model with email as primary identifier
2. OTPVerification - Stores OTPs for email verification
3. PasswordResetToken - Secure tokens for password reset
"""

import uuid
import random
import string
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


class CustomUserManager(BaseUserManager):
    """
    Custom manager for CustomUser.
    
    Manager handles the creation of users. We override it to:
    1. Use email as the primary identifier
    2. Normalize email addresses
    3. Handle superuser creation
    """
    
    def create_user(self, email, username, password=None, **extra_fields):
        """
        Create and save a regular user.
        
        Args:
            email: User's email address (required)
            username: User's username (required)
            password: User's password (optional for social auth)
            **extra_fields: Additional fields to set on the user
        """
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a username')
        
        # Normalize email - lowercase the domain part
        email = self.normalize_email(email)
        
        user = self.model(
            email=email,
            username=username,
            **extra_fields
        )
        
        # set_password() hashes the password
        # If password is None (social auth), user can't login with password
        user.set_password(password)
        user.save(using=self._db)
        
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        """
        Create and save a superuser.
        
        Superusers have:
        - is_staff = True (can access admin site)
        - is_superuser = True (has all permissions)
        - is_email_verified = True (skip email verification)
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_email_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, username, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User Model.
    
    Key differences from Django's default User:
    1. Uses email as the primary identifier (not username)
    2. Both email and username are required and unique
    3. Includes is_email_verified field
    4. Includes auth_provider to track how user signed up
    
    AbstractBaseUser provides:
    - password field with hashing
    - last_login field
    - is_active field
    
    PermissionsMixin provides:
    - is_superuser field
    - groups and user_permissions
    - Permission checking methods
    """
    
    # Authentication provider choices
    class AuthProvider(models.TextChoices):
        EMAIL = 'email', 'Email'
        GOOGLE = 'google', 'Google'
        APPLE = 'apple', 'Apple'
    
    # Primary fields
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the user"
    )
    
    email = models.EmailField(
        unique=True,
        max_length=255,
        help_text="User's email address - used for login"
    )
    
    username = models.CharField(
        unique=True,
        max_length=30,
        help_text="User's username - used for login and display"
    )
    
    # Email verification
    is_email_verified = models.BooleanField(
        default=False,
        help_text="Has the user verified their email address?"
    )
    
    # Authentication provider tracking
    auth_provider = models.CharField(
        max_length=20,
        choices=AuthProvider.choices,
        default=AuthProvider.EMAIL,
        help_text="How did the user sign up?"
    )
    
    # Social auth identifiers (nullable, set when using social login)
    google_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="Google account ID for OAuth"
    )
    
    apple_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="Apple account ID for OAuth"
    )
    
    # Django admin fields
    is_active = models.BooleanField(
        default=True,
        help_text="Is the user account active?"
    )
    
    is_staff = models.BooleanField(
        default=False,
        help_text="Can the user access the admin site?"
    )
    
    # Timestamps
    date_joined = models.DateTimeField(
        default=timezone.now,
        help_text="When did the user create their account?"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When was the user last updated?"
    )
    
    # Manager
    objects = CustomUserManager()
    
    # This field is used for authentication
    USERNAME_FIELD = 'email'
    
    # These fields are required when creating a superuser via createsuperuser
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return the username as the full name."""
        return self.username
    
    def get_short_name(self):
        """Return the username as the short name."""
        return self.username


class OTPVerification(models.Model):
    """
    OTP (One-Time Password) for email verification.
    
    Flow:
    1. User signs up → OTP created and emailed
    2. User enters OTP → We verify it's correct and not expired
    3. If valid → Mark user as verified, delete OTP
    
    Security features:
    - OTP expires after 10 minutes
    - Max 3 attempts, then new OTP required
    - OTP is deleted after successful verification
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    
    # Link to the user awaiting verification
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='otp_verifications'
    )
    
    # 6-digit OTP code
    otp_code = models.CharField(
        max_length=6,
        help_text="6-digit verification code"
    )
    
    # Expiry time (10 minutes from creation)
    expires_at = models.DateTimeField(
        help_text="When does this OTP expire?"
    )
    
    # Attempt tracking
    attempts = models.IntegerField(
        default=0,
        help_text="Number of failed verification attempts"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.user.email}"
    
    def save(self, *args, **kwargs):
        """Set expiry time if not already set."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(
                minutes=settings.OTP_EXPIRY_MINUTES
            )
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if OTP has expired."""
        return timezone.now() > self.expires_at
    
    @property
    def is_max_attempts_reached(self):
        """Check if max attempts (3) reached."""
        return self.attempts >= 3
    
    @staticmethod
    def generate_otp():
        """Generate a random 6-digit OTP."""
        return ''.join(random.choices(string.digits, k=6))


class PasswordResetToken(models.Model):
    """
    Token for password reset functionality.
    
    Flow:
    1. User requests password reset → Token created and emailed
    2. User clicks link with token → We verify token and show reset form
    3. User submits new password → We update password and delete token
    
    Security features:
    - Token expires after 1 hour
    - Token is a secure UUID (hard to guess)
    - Token is deleted after use
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    
    # Link to the user
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    
    # Secure token (UUID) - kept for the final reset step
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text="Secure token for password reset"
    )

    # NEW: 6-digit OTP code - used for the initial verification
    otp_code = models.CharField(
        max_length=6,
        null=True,
        blank=True,
        help_text="6-digit verification code"
    )

    
    # Expiry time (1 hour from creation)
    expires_at = models.DateTimeField(
        help_text="When does this token expire?"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Password reset for {self.user.email}"
    
    def save(self, *args, **kwargs):
        """Set expiry time if not already set."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if token has expired."""
        return timezone.now() > self.expires_at

    @staticmethod
    def generate_otp():
        """Generate a random 6-digit OTP."""
        return ''.join(random.choices(string.digits, k=6))


class PendingRegistration(models.Model):
    """
    Temporarily stores registration data until email is verified.
    
    Flow:
    1. User submits signup form → PendingRegistration created, OTP emailed
    2. User enters OTP → We verify it's correct and not expired
    3. If valid → Create actual User, delete PendingRegistration
    
    This ensures no user is created until email ownership is confirmed.
    
    Security features:
    - OTP expires after 10 minutes
    - Max 3 attempts, then new OTP required
    - Password is hashed before storage
    - Automatically cleaned up after verification or expiry
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    
    # Registration data (stored temporarily)
    email = models.EmailField(
        unique=True,
        max_length=255,
        help_text="Email to be verified"
    )
    
    username = models.CharField(
        max_length=30,
        help_text="Requested username"
    )
    
    # Password is stored hashed (using Django's make_password)
    password_hash = models.CharField(
        max_length=128,
        help_text="Hashed password"
    )
    
    # 6-digit OTP code
    otp_code = models.CharField(
        max_length=6,
        help_text="6-digit verification code"
    )
    
    # Expiry time (10 minutes from creation)
    expires_at = models.DateTimeField(
        help_text="When does this registration expire?"
    )
    
    # Attempt tracking
    attempts = models.IntegerField(
        default=0,
        help_text="Number of failed verification attempts"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Pending registration for {self.email}"
    
    def save(self, *args, **kwargs):
        """Set expiry time if not already set."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(
                minutes=settings.OTP_EXPIRY_MINUTES
            )
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if registration has expired."""
        return timezone.now() > self.expires_at
    
    @property
    def is_max_attempts_reached(self):
        """Check if max attempts (3) reached."""
        return self.attempts >= 3
    
    @staticmethod
    def generate_otp():
        """Generate a random 6-digit OTP."""
        return ''.join(random.choices(string.digits, k=6))
