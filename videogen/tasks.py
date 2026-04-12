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
    from django.core.cache import cache
    
    lock_key = f"video_task_lock_{project_id}"
    
    try:
        project = VideoProject.objects.get(id=project_id)
        
        # Smart Exit: Stop only if it's already in a terminal state AND branding is handled
        is_trial = project.user.subscription.is_trial
        needs_branding = is_trial and not project.is_watermarked
        
        if project.status == VideoProject.StatusChoice.VIDEO_FAILED:
            cache.delete(lock_key)
            return f"Project {project_id} failed."
            
        if project.status == VideoProject.StatusChoice.VIDEO_COMPLETED and not needs_branding:
            cache.delete(lock_key)
            return f"Project {project_id} already completed and branded."

        if not project.heygen_video_id:
            logger.warning(f"Project {project_id} has no HeyGen video ID. Retrying...")
            raise self.retry(countdown=30)

        result = heygen_service.get_video_status(project.heygen_video_id)
        heygen_status = result["status"]
        
        logger.info(f"Monitoring status for {project_id}: {heygen_status}")

        if heygen_status == 'completed':
            project.status = VideoProject.StatusChoice.VIDEO_COMPLETED
            project.video_url = result["video_url"] or ""
            
            # Download and save/brand video file in the background
            if result["video_url"]:
                from .services import watermark_service
                try:
                    # Logic matches robust branding:
                    # Detect if branding is needed (Trial + not is_watermarked)
                    base_filename = f"{project.id}"
                    final_filename = f"{base_filename}_branded.mp4" if is_trial else f"{base_filename}.mp4"
                    
                    logger.info(f"Task: Downloading and processing video for project {project_id}...")
                    
                    video_file_obj = heygen_service.download_video(result["video_url"], final_filename)
                    
                    # Read bytes once to avoid pointer issues
                    video_content_bytes = video_file_obj.read()
                    
                    if is_trial:
                        logger.info(f"Task: Applying scaled watermark to {project_id}...")
                        video_file_obj = watermark_service.apply_watermark(
                            video_content_bytes, final_filename
                        )
                        project.is_watermarked = True
                    else:
                        from django.core.files.base import ContentFile
                        video_file_obj = ContentFile(video_content_bytes, name=final_filename)

                    # CRITICAL: Force clear the path on disk to prevent Django suffixes
                    import os
                    from django.conf import settings
                    # Construct the relative path Django would use
                    relative_path = os.path.join("videos", project.created_at.strftime("%Y/%m"), final_filename)
                    full_media_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                    
                    if os.path.exists(full_media_path):
                        try:
                            os.remove(full_media_path)
                            logger.info(f"Task: Forced delete of existing disk file: {final_filename}")
                        except Exception as e:
                            logger.warning(f"Task: Could not force delete disk file: {e}")

                    # Also cleanup the OLD file record if it exists in DB
                    if project.video_file:
                        try:
                            project.video_file.delete(save=False)
                        except Exception as e:
                            logger.warning(f"Task: Could not delete DB-linked file: {e}")

                    project.video_file.save(final_filename, video_file_obj, save=False)
                    logger.info(f"Task: Video file saved successfully for {project_id}")
                    
                except Exception as e:
                    logger.error(f"Task: Failed to process video file: {e}")
                    project.video_status_message = f"Background processing failed: {e}"
            
            project.video_status_message = "Video completed successfully."
            project.save()
            
            # Increment video count (only once)
            try:
                project.user.subscription.increment_video_count()
            except Exception as e:
                logger.error(f"Failed to increment video count: {e}")
            
            # Send Email
            send_video_ready_email(project)
            cache.delete(lock_key)
            return f"Video {project_id} completed and branded."

        elif heygen_status == 'failed':
            project.status = VideoProject.StatusChoice.VIDEO_FAILED
            project.video_status_message = result.get("message", "Video generation failed at HeyGen.")
            project.save()
            cache.delete(lock_key)
            return f"Video {project_id} failed."
            
        else:
            # Still processing or pending -> Update message and retry in 30s
            project.video_status_message = result.get("message", f"Video status: {heygen_status}")
            project.save()
            raise self.retry(countdown=30)
            
    except VideoProject.DoesNotExist:
        cache.delete(lock_key)
        return "Project not found"
    except Exception as e:
        # Only retry if it's not a Celery Retry exception
        from celery.exceptions import Retry
        if isinstance(e, Retry):
            raise e
        
        cache.delete(lock_key)
        logger.error(f"Error monitoring video {project_id}: {e}")
        raise self.retry(exc=e, countdown=60)