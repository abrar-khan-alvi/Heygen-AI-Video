import logging
import os
import requests
from celery import shared_task
from django.core.files.base import ContentFile

from .models import ProductPromoProject
from .services import heygen_service

logger = logging.getLogger(__name__)

# Lock key MUST match the key used in views.py
_LOCK_PREFIX = "promo_task_lock_"


@shared_task(name="productpromo.tasks.monitor_promo_video_task", bind=True, max_retries=60)
def monitor_promo_video_task(self, project_id):
    """
    Monitor HeyGen video status, download the final file, apply watermark
    for Free Trial users, and increment the subscription video counter.

    Mirrors videogen/tasks.py monitor_video_status_task exactly.
    """
    from django.core.cache import cache

    lock_key = f"{_LOCK_PREFIX}{project_id}"

    try:
        project = ProductPromoProject.objects.select_related(
            "user", "user__subscription", "user__subscription__plan"
        ).get(id=project_id)

        # ── Terminal state checks ──────────────────────────────────────────────
        if project.status == ProductPromoProject.StatusChoice.VIDEO_FAILED:
            cache.delete(lock_key)
            return f"Promo project {project_id} already failed."

        if project.status == ProductPromoProject.StatusChoice.VIDEO_COMPLETED and project.video_file:
            cache.delete(lock_key)
            return f"Promo project {project_id} already completed and processed."

        # ── Poll HeyGen ────────────────────────────────────────────────────────
        result = heygen_service.get_video_status(project.heygen_video_id)
        heygen_status = result.get("status")
        logger.info(f"Promo task polling {project_id}: {heygen_status}")

        # ── COMPLETED ─────────────────────────────────────────────────────────
        if heygen_status == "completed":
            project.status    = ProductPromoProject.StatusChoice.VIDEO_COMPLETED
            project.video_url = result.get("video_url") or ""

            if project.video_url:
                try:
                    # Determine if this user is on a Free Trial
                    is_trial = project.user.subscription.is_trial
                    base_filename   = f"promo_{project.id}"
                    final_filename  = f"{base_filename}_branded.mp4" if is_trial else f"{base_filename}.mp4"

                    logger.info(f"Promo task: downloading video for {project_id}...")
                    resp = requests.get(project.video_url, timeout=120)
                    resp.raise_for_status()
                    video_bytes = resp.content

                    # Apply watermark for Free Trial users (mirrors videogen)
                    if is_trial:
                        logger.info(f"Promo task: applying watermark for trial user {project.user.id}...")
                        from videogen.services import watermark_service
                        video_file_obj = watermark_service.apply_watermark(video_bytes, final_filename)
                        project.is_watermarked = True
                    else:
                        video_file_obj = ContentFile(video_bytes, name=final_filename)

                    # Force-delete any existing disk file to prevent Django adding suffixes
                    from django.conf import settings
                    from datetime import datetime
                    relative_path = os.path.join(
                        "promo_videos",
                        project.created_at.strftime("%Y/%m"),
                        final_filename,
                    )
                    full_media_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                    if os.path.exists(full_media_path):
                        try:
                            os.remove(full_media_path)
                            logger.info(f"Promo task: removed stale disk file {final_filename}")
                        except Exception as e:
                            logger.warning(f"Promo task: could not remove stale disk file: {e}")

                    # Clean up old DB-linked file record
                    if project.video_file:
                        try:
                            project.video_file.delete(save=False)
                        except Exception as e:
                            logger.warning(f"Promo task: could not delete old DB file record: {e}")

                    project.video_file.save(final_filename, video_file_obj, save=False)
                    logger.info(f"Promo task: video file saved for {project_id}")

                except Exception as e:
                    logger.error(f"Promo task: failed to process video file: {e}")
                    project.video_status_message = f"Download/branding failed: {e}"

            project.video_status_message = "Video completed and downloaded."
            project.save()

            # ── Increment subscription video counter (only once) ───────────────
            try:
                project.user.subscription.increment_video_count()
                logger.info(
                    f"Promo task: subscription counter incremented for user "
                    f"{project.user.id} (project {project_id})"
                )
            except Exception as e:
                logger.error(f"Promo task: failed to increment video count: {e}")

            cache.delete(lock_key)
            return f"Promo project {project_id} completed."

        # ── FAILED ────────────────────────────────────────────────────────────
        elif heygen_status == "failed":
            project.status               = ProductPromoProject.StatusChoice.VIDEO_FAILED
            project.video_status_message = result.get("message", "Video generation failed at HeyGen.")
            project.save()
            cache.delete(lock_key)
            return f"Promo project {project_id} failed."

        # ── STILL PROCESSING ──────────────────────────────────────────────────
        else:
            project.video_status_message = result.get("message") or f"Video status: {heygen_status}"
            project.save()
            raise self.retry(countdown=30)

    except ProductPromoProject.DoesNotExist:
        cache.delete(lock_key)
        return f"Promo project {project_id} not found."

    except Exception as e:
        from celery.exceptions import Retry
        if isinstance(e, Retry):
            raise
        cache.delete(lock_key)
        logger.error(f"Promo task: unexpected error for {project_id}: {e}")
        raise self.retry(exc=e, countdown=60)
