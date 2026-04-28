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

        # Determine if this user needs watermarking
        is_trial = project.user.subscription.is_trial
        needs_branding = is_trial and not project.is_watermarked

        # Only exit early if the file is ready AND branding is done
        if project.status == ProductPromoProject.StatusChoice.VIDEO_COMPLETED and project.video_file and not needs_branding:
            cache.delete(lock_key)
            return f"Promo project {project_id} already completed and processed."

        # ── Step 1: Resolve video_id from session if missing ──────────────────
        # v2 Standard API: video_id is already set, session_id is empty → skip
        # v3 Video Agent:  session_id is set, must be resolved to video_id first
        if not project.heygen_video_id:
            if not project.heygen_session_id:
                cache.delete(lock_key)
                return f"Promo project {project_id} has no session ID."
            
            logger.info(f"Promo task: polling session {project.heygen_session_id} for {project_id}")
            session_result = heygen_service.get_session_status(project.heygen_session_id)
            video_id = session_result.get("video_id")
            
            if video_id:
                project.heygen_video_id = video_id
                project.save(update_fields=["heygen_video_id"])
                logger.info(f"Promo task: resolved to video_id {video_id} for {project_id}")
            else:
                session_status = session_result.get("status", "unknown")
                project.video_status_message = f"HeyGen session: {session_status}"
                project.save(update_fields=["video_status_message"])
                raise self.retry(countdown=20)

        # ── Step 2: Poll HeyGen ────────────────────────────────────────────────
        is_v2 = not project.heygen_session_id
        if is_v2:
            result = heygen_service.get_video_status_standard(project.heygen_video_id)
        else:
            result = heygen_service.get_video_status(project.heygen_video_id)
        heygen_status = result.get("status")
        logger.info(f"Promo task polling {project_id} (v{'2' if is_v2 else '3'}): {heygen_status}")

        # ── COMPLETED ─────────────────────────────────────────────────────────
        if heygen_status == "completed":
            project.status    = ProductPromoProject.StatusChoice.VIDEO_COMPLETED
            project.video_url = result.get("video_url") or ""

            if project.video_url and (not project.video_file or needs_branding):
                base_filename  = f"promo_{project.id}"
                final_filename = f"{base_filename}_branded.mp4" if is_trial else f"{base_filename}.mp4"

                logger.info(f"Promo task: downloading video for {project_id}...")
                resp = requests.get(project.video_url, timeout=120)
                resp.raise_for_status()
                video_bytes = resp.content
                logger.info(f"Promo task: downloaded {len(video_bytes)} bytes for {project_id}")

                if is_trial:
                    logger.info(f"Promo task: applying watermark for trial user {project.user.id}...")
                    from videogen.services import watermark_service
                    video_file_obj = watermark_service.apply_watermark(video_bytes, final_filename)
                    project.is_watermarked = True
                    logger.info(f"Promo task: watermark applied for {project_id}")
                else:
                    video_file_obj = ContentFile(video_bytes, name=final_filename)

                # Force-delete stale disk file to prevent Django adding suffixes
                from django.conf import settings
                relative_path = os.path.join(
                    "product_promo", "videos",
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

            project.video_status_message = "Video completed and downloaded."
            project.save()

            # ── Increment subscription counter — atomic, once-only ─────────────
            # Use a DB-level update to atomically claim the is_counted flag.
            # Only the process that flips is_counted False→True will increment,
            # preventing race conditions between this task and the status view.
            claimed = ProductPromoProject.objects.filter(
                pk=project.pk, is_counted=False
            ).update(is_counted=True)

            if claimed:
                try:
                    project.user.subscription.increment_video_count()
                    logger.info(
                        f"Promo task: subscription counter incremented for user "
                        f"{project.user.id} (project {project_id})"
                    )
                except Exception as e:
                    logger.error(f"Promo task: failed to increment video count: {e}")
                    # Roll back the flag so the view can retry
                    ProductPromoProject.objects.filter(pk=project.pk).update(is_counted=False)
            else:
                logger.info(f"Promo task: counter already claimed for {project_id}, skipping.")

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
