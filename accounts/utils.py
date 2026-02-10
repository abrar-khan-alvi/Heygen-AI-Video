"""
Utility functions for accounts app.

This module contains helper functions for:
1. Sending emails (OTP, password reset) with HTML templates
2. Token generation and validation
"""

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from .models import OTPVerification, PasswordResetToken


def send_otp_email(user):
    """
    Generate OTP and send it via email with beautiful HTML template.
    
    Args:
        user: CustomUser instance
    
    Returns:
        OTPVerification instance
    """
    # Delete existing OTPs for this user
    OTPVerification.objects.filter(user=user).delete()
    
    # Generate new OTP
    otp_code = OTPVerification.generate_otp()
    
    # Create OTP record
    otp = OTPVerification.objects.create(
        user=user,
        otp_code=otp_code
    )
    
    # Email content
    subject = '🔐 Verify Your Email - OTP Code'
    
    # Plain text version (fallback)
    text_content = f"""
Hello {user.username},

Your OTP code for email verification is: {otp_code}

This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.

If you didn't request this, please ignore this email.

Best regards,
The Team
    """
    
    # HTML version from template
    html_content = render_to_string('emails/otp_verification.html', {
        'username': user.username,
        'otp_code': otp_code,
        'expiry_minutes': settings.OTP_EXPIRY_MINUTES,
    })
    
    # Send email with both text and HTML versions
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)
    
    return otp


def send_password_reset_email(user):
    """
    Generate password reset token and send email with beautiful HTML template.
    
    Args:
        user: CustomUser instance
    
    Returns:
        PasswordResetToken instance
    """
    # Delete existing tokens for this user
    PasswordResetToken.objects.filter(user=user).delete()
    
    # Create new token with OTP
    reset_token = PasswordResetToken.objects.create(
        user=user,
        otp_code=PasswordResetToken.generate_otp()
    )
    
    # Email content
    subject = '🔑 Reset Your Password - OTP Code'
    
    # Plain text version (fallback)
    text_content = f"""
Hello {user.username},

You requested to reset your password. Your OTP code is:

{reset_token.otp_code}

This code will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
The Team
    """
    
    # HTML version from template
    html_content = render_to_string('emails/password_reset.html', {
        'username': user.username,
        'otp_code': reset_token.otp_code,
    })
    
    # Send email with both text and HTML versions
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)
    
    return reset_token


def verify_otp(user, otp_code):
    """
    Verify OTP code for a user.
    
    Args:
        user: CustomUser instance
        otp_code: String OTP code to verify
    
    Returns:
        Tuple (success: bool, message: str)
    """
    try:
        otp = OTPVerification.objects.get(user=user)
    except OTPVerification.DoesNotExist:
        return False, "No OTP found. Please request a new one."
    
    # Check if max attempts reached
    if otp.is_max_attempts_reached:
        otp.delete()
        return False, "Maximum attempts reached. Please request a new OTP."
    
    # Check if expired
    if otp.is_expired:
        otp.delete()
        return False, "OTP has expired. Please request a new one."
    
    # Verify OTP
    if otp.otp_code != otp_code:
        otp.attempts += 1
        otp.save()
        remaining = 3 - otp.attempts
        return False, f"Invalid OTP. {remaining} attempts remaining."
    
    # Success! Mark user as verified and delete OTP
    user.is_email_verified = True
    user.save()
    otp.delete()
    
    return True, "Email verified successfully!"


def verify_password_reset_token(token):
    """
    Verify password reset token.
    
    Args:
        token: UUID token string
    
    Returns:
        Tuple (user: CustomUser or None, message: str)
    """
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        return None, "Invalid or expired reset token."
    
    if reset_token.is_expired:
        reset_token.delete()
        return None, "Reset token has expired. Please request a new one."
    
    return reset_token.user, "Token valid."
