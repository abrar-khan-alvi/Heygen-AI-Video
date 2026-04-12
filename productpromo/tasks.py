import logging
from celery import shared_task
import requests
from django.core.files.base import ContentFile
from .models import ProductPromoProject
from .services import heygen_service

logger = logging.getLogger(__name__)

@shared_task(name="productpromo.tasks.monitor_promo_video_task", bind=True, max_retries=60)
def monitor_promo_video_task(self, project_id):
    """
    Monitor HeyGen video status and download the final file locally.
    """
    from django.core.cache import cache
    
    lock_key = f"promo_lock_{project_id}"
    
    try:
        project = ProductPromoProject.objects.get(id=project_id)
        
        # Terminal states
        if project.status == ProductPromoProject.StatusChoice.VIDEO_FAILED:
            cache.delete(lock_key)
            return "Already failed."
        if project.status == ProductPromoProject.StatusChoice.VIDEO_COMPLETED and project.video_file:
            cache.delete(lock_key)
            return "Already fully processed."

        # Check status
        result = heygen_service.get_video_status(project.heygen_video_id)
        status = result.get("status")

        if status == "completed":
            project.status = ProductPromoProject.StatusChoice.VIDEO_COMPLETED
            project.video_url = result.get("video_url")
            
            # Download file
            if project.video_url:
                try:
                    resp = requests.get(project.video_url, timeout=120)
                    resp.raise_for_status()
                    filename = f"promo_{project.id}.mp4"
                    project.video_file.save(filename, ContentFile(resp.content), save=False)
                except Exception as e:
                    logger.error(f"Failed to download promo video: {e}")

            project.video_status_message = "Video completed and downloaded."
            project.save()
            cache.delete(lock_key)
            return f"Promo project {project.id} completed."

        elif status == "failed":
            project.status = ProductPromoProject.StatusChoice.VIDEO_FAILED
            project.video_status_message = result.get("message", "Unknown error")
            project.save()
            cache.delete(lock_key)
            return f"Promo project {project.id} failed."

        else:
            # Still processing
            project.video_status_message = f"Video status: {status}"
            project.save()
            raise self.retry(countdown=30)

    except ProductPromoProject.DoesNotExist:
        cache.delete(lock_key)
        return "Project not found."
    except Exception as e:
        # Handle retry
        from celery.exceptions import Retry
        if isinstance(e, Retry):
            raise
        
        cache.delete(lock_key)
        logger.error(f"Error monitoring promo video {project_id}: {e}")
        raise self.retry(exc=e, countdown=60)
