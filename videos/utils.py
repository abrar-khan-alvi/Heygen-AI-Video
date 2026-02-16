from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_video_ready_email(video_project):
    """
    Sends an email notification to the user that their video is ready.
    """
    try:
        user = video_project.user
        subject = "Your AI Video is Ready! 🎬"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]

        # Context for the template
        context = {
            'user': user,
            'project_title': video_project.title or "Untitled Project",
            'video_url': video_project.video_url,
        }

        # Render templates
        text_content = render_to_string('emails/video_ready.txt', context)
        html_content = render_to_string('emails/video_ready.html', context)

        # Create email
        msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        print(f"DEBUG: Email SENT successfully to {user.email}") # Force print to logs
        logger.info(f"Video ready email sent to {user.email} for project {video_project.id}")
        return True

    except Exception as e:
        print(f"DEBUG: Email FAILED to send: {e}") # Force print to logs
        logger.error(f"Failed to send video ready email to {video_project.user.email}: {e}")
        return False
