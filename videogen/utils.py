import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

def send_video_ready_email(project):
    """
    Send an email to the user when their video is ready.
    """
    user = project.user
    subject = '🎬 Your AI Video is Ready!'
    
    # Plain text version
    text_content = f"""
Hello {user.username},

Great news! Your video "{project.title}" has been successfully generated and is ready to watch.

You can view it here: {settings.FRONTEND_URL}/videos/{project.id}

Thank you for using our service!
    """
    
    # HTML version (optional: create a template if needed)
    # For now, we'll just use a simple string or reuse an existing template style
    try:
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #4A90E2;">Your AI Video is Ready!</h2>
                <p>Hello <strong>{user.username}</strong>,</p>
                <p>Great news! Your video <strong>"{project.title}"</strong> has been successfully generated.</p>
                <p style="margin: 30px 0;">
                    <a href="{settings.FRONTEND_URL}/videos/{project.id}" 
                       style="background-color: #4A90E2; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        View Your Video
                    </a>
                </p>
                <p>Thank you for using our service!</p>
                <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
                <p style="font-size: 12px; color: #888;">If you didn't request this, please ignore this email.</p>
            </body>
        </html>
        """
        
        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Video ready email sent to {user.email} for project {project.id}")
    except Exception as e:
        logger.error(f"Failed to send video ready email: {e}")
