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
        project = VideoProject.objects.select_related(
            "user", "user__subscription", "user__subscription__plan"
        ).get(id=project_id)
        
        # Smart Exit: Stop only if it's already in a terminal state AND branding is handled
        is_trial = project.user.subscription.is_trial
        needs_branding = is_trial and not project.is_watermarked
        
        if project.status == VideoProject.StatusChoice.VIDEO_FAILED:
            cache.delete(lock_key)
            return f"Project {project_id} failed."
            
        if project.status == VideoProject.StatusChoice.VIDEO_COMPLETED and not needs_branding:
            cache.delete(lock_key)
            return f"Project {project_id} already completed and branded."

        # ── Step 1: Resolve video_id from session if missing ──────────────────
        # v2 Standard API: video_id is set immediately, session_id is empty → skip this step
        # v3 Video Agent: session_id is set, video_id must be resolved from session
        if not project.heygen_video_id:
            if not project.heygen_session_id:
                cache.delete(lock_key)
                return f"Project {project_id} has no session ID."
            
            logger.info(f"Task: polling session {project.heygen_session_id} for project {project_id}")
            session_result = heygen_service.get_session_status(project.heygen_session_id)
            video_id = session_result.get("video_id")
            
            if video_id:
                project.heygen_video_id = video_id
                project.save(update_fields=["heygen_video_id"])
                logger.info(f"Task: session resolved to video_id {video_id} for {project_id}")
            else:
                session_status = session_result.get("status", "unknown")
                project.video_status_message = f"HeyGen session: {session_status}"
                project.save(update_fields=["video_status_message"])
                raise self.retry(countdown=20)

        # ── Step 2: Poll video status ─────────────────────────────────────────
        # Use v1 endpoint for v2-generated videos (session_id empty = v2 mode)
        # Use v3 endpoint for legacy v3 agent videos (session_id populated)
        is_v2 = not project.heygen_session_id
        if is_v2:
            result = heygen_service.get_video_status_standard(project.heygen_video_id)
        else:
            result = heygen_service.get_video_status(project.heygen_video_id)
        heygen_status = result["status"]
        
        logger.info(f"Monitoring status for {project_id} (v{'2' if is_v2 else '3'}): {heygen_status}")

        if heygen_status == 'completed':
            project.status = VideoProject.StatusChoice.VIDEO_COMPLETED
            project.video_url = result["video_url"] or ""
            
            # Download and watermark only if file not yet saved (or branding still needed)
            if result["video_url"] and (not project.video_file or needs_branding):
                from .services import watermark_service
                base_filename = f"{project.id}"
                final_filename = f"{base_filename}_branded.mp4" if is_trial else f"{base_filename}.mp4"
                
                logger.info(f"Task: Downloading video for project {project_id}...")
                video_file_obj = heygen_service.download_video(result["video_url"], final_filename)
                video_content_bytes = video_file_obj.read()
                logger.info(f"Task: Downloaded {len(video_content_bytes)} bytes for {project_id}")
                
                if is_trial:
                    logger.info(f"Task: Applying watermark to {project_id}...")
                    video_file_obj = watermark_service.apply_watermark(
                        video_content_bytes, final_filename
                    )
                    project.is_watermarked = True
                    logger.info(f"Task: Watermark applied for {project_id}")
                else:
                    from django.core.files.base import ContentFile
                    video_file_obj = ContentFile(video_content_bytes, name=final_filename)

                # Force-clear disk path to prevent Django adding suffix
                import os
                from django.conf import settings
                relative_path = os.path.join("videos", project.created_at.strftime("%Y/%m"), final_filename)
                full_media_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                
                if os.path.exists(full_media_path):
                    try:
                        os.remove(full_media_path)
                        logger.info(f"Task: Removed stale disk file: {final_filename}")
                    except Exception as e:
                        logger.warning(f"Task: Could not remove stale disk file: {e}")

                if project.video_file:
                    try:
                        project.video_file.delete(save=False)
                    except Exception as e:
                        logger.warning(f"Task: Could not delete DB-linked file: {e}")

                project.video_file.save(final_filename, video_file_obj, save=False)
                logger.info(f"Task: Video file saved successfully for {project_id}")
            
            project.video_status_message = "Video completed successfully."
            project.save()
            
            # ── Increment subscription counter — atomic, once-only ─────────────
            # Regenerations count against the regeneration quota; normal videos
            # count against the monthly video quota.
            if project.is_regeneration:
                claimed = VideoProject.objects.filter(
                    pk=project.pk, is_regen_counted=False
                ).update(is_regen_counted=True)

                if claimed:
                    try:
                        project.user.subscription.increment_regeneration_count()
                        logger.info(f"Task: regeneration counter incremented for user {project.user.id} (project {project_id})")
                    except Exception as e:
                        logger.error(f"Failed to increment regeneration count: {e}")
                        VideoProject.objects.filter(pk=project.pk).update(is_regen_counted=False)
                else:
                    logger.info(f"Task: regen counter already claimed for {project_id}, skipping.")
            else:
                claimed = VideoProject.objects.filter(
                    pk=project.pk, is_counted=False
                ).update(is_counted=True)

                if claimed:
                    try:
                        project.user.subscription.increment_video_count()
                        logger.info(f"Task: subscription counter incremented for user {project.user.id} (project {project_id})")
                    except Exception as e:
                        logger.error(f"Failed to increment video count: {e}")
                        VideoProject.objects.filter(pk=project.pk).update(is_counted=False)
                else:
                    logger.info(f"Task: counter already claimed for {project_id}, skipping.")

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