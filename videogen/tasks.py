"""
Celery tasks for videogen.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="videogen.tasks.sync_avatars_task")
def sync_avatars_task():
    from django.core.management import call_command
    logger.info("Starting weekly avatar sync...")
    try:
        call_command("sync_avatars")
        logger.info("Avatar sync completed.")
        return "Avatar sync completed."
    except Exception as e:
        logger.error(f"Avatar sync failed: {e}")
        raise


@shared_task(name="videogen.tasks.monitor_video_status_task", bind=True, max_retries=60)
def monitor_video_status_task(self, project_id):
    """
    Background task to monitor video status.
    Polls HeyGen API until completed or failed.
    """
    from .models import VideoProject
    from .services import heygen_service
    from .utils import send_video_ready_email
    
    try:
        project = VideoProject.objects.get(id=project_id)
        
        # Stop if already done or in a terminal state
        if project.status in [
            VideoProject.StatusChoice.VIDEO_COMPLETED,
            VideoProject.StatusChoice.VIDEO_FAILED,
        ]:
            return f"Project {project_id} already reached final status: {project.status}"

        if not project.heygen_video_id:
            logger.warning(f"Project {project_id} has no HeyGen video ID. Retrying...")
            raise self.retry(countdown=30)

        result = heygen_service.get_video_status(project.heygen_video_id)
        heygen_status = result["status"]
        
        logger.info(f"Monitoring status for {project_id}: {heygen_status}")

        if heygen_status == 'completed':
            project.status = VideoProject.StatusChoice.VIDEO_COMPLETED
            project.video_url = result["video_url"] or ""
            
            # Download and save video file
            if result["video_url"]:
                try:
                    filename = f"{project.id}.mp4"
                    video_content = heygen_service.download_video(result["video_url"], filename)
                    project.video_file.save(filename, video_content, save=False)
                except Exception as e:
                    logger.error(f"Failed to save video file in task: {e}")
            
            project.video_status_message = "Video completed successfully."
            project.save()
            
            # Increment video count
            try:
                project.user.subscription.increment_video_count()
            except Exception as e:
                logger.error(f"Failed to increment video count: {e}")
            
            # Send Email
            send_video_ready_email(project)
            return f"Video {project_id} completed."

        elif heygen_status == 'failed':
            project.status = VideoProject.StatusChoice.VIDEO_FAILED
            project.video_status_message = result.get("message", "Video generation failed at HeyGen.")
            project.save()
            return f"Video {project_id} failed."
            
        else:
            # Still processing or pending -> Update message and retry in 30s
            project.video_status_message = result.get("message", f"Video status: {heygen_status}")
            project.save()
            raise self.retry(countdown=30)
            
    except VideoProject.DoesNotExist:
        return "Project not found"
    except Exception as e:
        # Only retry if it's not a Celery Retry exception
        from celery.exceptions import Retry
        if isinstance(e, Retry):
            raise e
        logger.error(f"Error monitoring video {project_id}: {e}")
        raise self.retry(exc=e, countdown=60)