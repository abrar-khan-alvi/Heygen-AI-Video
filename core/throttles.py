"""
API Rate Limiting.

Add to settings.py:

REST_FRAMEWORK = {
    ...existing settings...
    'DEFAULT_THROTTLE_CLASSES': [
        'core.throttles.AnonBurstThrottle',
        'core.throttles.AnonSustainedThrottle',
        'core.throttles.UserBurstThrottle',
        'core.throttles.UserSustainedThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon_burst': '10/minute',
        'anon_sustained': '100/hour',
        'user_burst': '30/minute',
        'user_sustained': '500/hour',
        'signup': '5/hour',
        'otp': '5/minute',
        'video_generate': '10/hour',
        'script_generate': '20/hour',
    },
}
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


# ── Global throttles (applied to all endpoints via DEFAULT_THROTTLE_CLASSES) ─

class AnonBurstThrottle(AnonRateThrottle):
    scope = "anon_burst"


class AnonSustainedThrottle(AnonRateThrottle):
    scope = "anon_sustained"


class UserBurstThrottle(UserRateThrottle):
    scope = "user_burst"


class UserSustainedThrottle(UserRateThrottle):
    scope = "user_sustained"


# ── Endpoint-specific throttles (applied per-view) ──────────────────────────

class SignupThrottle(AnonRateThrottle):
    """Limit signups to prevent abuse."""
    scope = "signup"


class OTPThrottle(AnonRateThrottle):
    """Limit OTP requests to prevent brute-force."""
    scope = "otp"


class VideoGenerateThrottle(UserRateThrottle):
    """Limit video generation requests."""
    scope = "video_generate"


class ScriptGenerateThrottle(UserRateThrottle):
    """Limit script generation requests."""
    scope = "script_generate"