from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def send_otp_email_task(self, email, subject, text_content, html_content):
    """
    Task to send OTP email asynchronously.
    """
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        return "OTP Email sent successfully"
    except Exception as e:
        logger.error(f"Failed to send OTP email: {e}")
        raise self.retry(exc=e, countdown=60)  # Retry in 1 minute

@shared_task(bind=True)
def send_password_reset_email_task(self, email, subject, text_content, html_content):
    """
    Task to send Password Reset email asynchronously.
    """
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        return "Password Reset Email sent successfully"
    except Exception as e:
        logger.error(f"Failed to send Password Reset email: {e}")
        raise self.retry(exc=e, countdown=60)

