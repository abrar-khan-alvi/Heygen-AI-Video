"""
Django settings for core project.

This file is configured for:
- JWT Authentication with SimpleJWT
- Django Rest Framework with API versioning
- CORS support for frontend integration
- Email sending for OTP verification
"""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
# In production, set this via environment variable
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# Hosts allowed to access this Django application
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

INSTALLED_APPS = [
    # Django built-in apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',                    # Django REST Framework
    'rest_framework_simplejwt',          # JWT authentication
    'rest_framework_simplejwt.token_blacklist',  # Allow logout by blacklisting tokens
    'corsheaders',                       # Cross-Origin Resource Sharing
    
    # Local apps
    'accounts',                          # Our authentication app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS - must be before CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# =============================================================================
# DATABASE
# Using SQLite for development. For production, use PostgreSQL/MySQL
# =============================================================================

# Use environment variable for database path, defaults to project root
# In Docker, this will be /app/data/db.sqlite3 (mounted volume)
import os
DB_DIR = os.getenv('DB_DIR', BASE_DIR)
if isinstance(DB_DIR, str):
    from pathlib import Path
    DB_DIR = Path(DB_DIR)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DB_DIR / 'db.sqlite3',
    }
}


# =============================================================================
# CUSTOM USER MODEL
# IMPORTANT: This must be set BEFORE running first migration
# =============================================================================

AUTH_USER_MODEL = 'accounts.CustomUser'


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},  # Minimum 8 characters
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================

REST_FRAMEWORK = {
    # Use JWT for authentication by default
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    
    # Require authentication for all endpoints by default
    # Individual views can override this with permission_classes = [AllowAny]
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    
    # API Versioning - use URL path like /api/v1/
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
    'VERSION_PARAM': 'version',
}


# =============================================================================
# JWT SETTINGS (SimpleJWT)
# =============================================================================

SIMPLE_JWT = {
    # Access token: Short-lived, used for API requests
    # Client stores in memory (not localStorage for security)
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=int(os.getenv('ACCESS_TOKEN_LIFETIME_MINUTES', 15))
    ),
    
    # Refresh token: Long-lived, used to get new access tokens
    # Client stores securely (httpOnly cookie recommended)
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=int(os.getenv('REFRESH_TOKEN_LIFETIME_DAYS', 7))
    ),
    
    # Rotate refresh tokens - issue new refresh token with each refresh
    # This limits the damage if a refresh token is stolen
    'ROTATE_REFRESH_TOKENS': True,
    
    # Blacklist old refresh tokens after rotation
    # Prevents reuse of old tokens
    'BLACKLIST_AFTER_ROTATION': True,
    
    # Algorithm used to sign tokens
    'ALGORITHM': 'HS256',
    
    # Key used to sign tokens (uses Django's SECRET_KEY)
    'SIGNING_KEY': SECRET_KEY,
    
    # Token type claim
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    
    # User identification in token
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}


# =============================================================================
# CORS SETTINGS
# =============================================================================

# For development, allow all origins
# In production, specify your frontend URL
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')

# Allow credentials (cookies, auth headers)
CORS_ALLOW_CREDENTIALS = True


# =============================================================================
# EMAIL SETTINGS (for OTP and password reset)
# =============================================================================

# Email backend - console for development, SMTP for production
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND', 
    'django.core.mail.backends.console.EmailBackend'  # Prints emails to console
)

# SMTP settings (used when EMAIL_BACKEND is not console)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# Default "from" email address
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@example.com')


# =============================================================================
# FRONTEND URL (for password reset links)
# =============================================================================

FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')


# =============================================================================
# OTP SETTINGS
# =============================================================================

OTP_EXPIRY_MINUTES = 10  # OTP expires after 10 minutes


# =============================================================================
# GOOGLE OAUTH SETTINGS
# =============================================================================

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')


# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# =============================================================================
# STATIC FILES
# =============================================================================

STATIC_URL = 'static/'


# =============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
