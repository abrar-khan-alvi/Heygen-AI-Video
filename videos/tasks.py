from celery import shared_task
from django.conf import settings
from .models import VideoProject
from .heygen_service import HeyGenClient
import logging
import time

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def generate_video_task(self, project_id):
    """
    Celery task to initiate video generation with HeyGen Video Agent.
    """
    try:
        project = VideoProject.objects.get(id=project_id)
        project.status = VideoProject.Status.PROCESSING
        project.save()

        # Generate the video script using Gemini AI
        from .gemini_service import GeminiService
        try:
            gemini_service = GeminiService()
            script_json = gemini_service.generate_script(
                title=project.title,
                industry=project.industry,
                service_description=project.service_description,
                gender=project.gender,
                outfit=project.avatar_outfit,
                background=project.background_type,
                duration="30 seconds"
            )
            
            # Parse the JSON since we forced response_mime_type="application/json"
            import json
            script_data = json.loads(script_json)
            script_text = script_data.get('script_text', '')
            
            if not script_text:
                 raise ValueError("Gemini returned invalid script_text.")
                 
        except Exception as e:
            logger.error(f"Failed to generate Gemini script for Project {project_id}: {e}")
            project.status = VideoProject.Status.FAILED
            project.save()
            return f"Failed to generate script: {e}"

        # Construct the prompt instructing HeyGen to speak the generated script
        prompt = (
            f"Create a high-quality marketing video for the {project.industry} industry. "
            f"Video Title: {project.title}. "
            f"Service Description: {project.service_description}. "
            f"The presenter is a {project.gender}. "
            f"The background is a {project.background_type}. "
            f"The presenter is wearing {project.avatar_outfit} attire. "
            f"Please speak the following exact script naturally and professionally:\n\n"
            f"\"{script_text}\"\n\n"
            f"Make sure to engage the audience and maintain a professional demeanor suitable for social media. "
            f"The video duration must be between 30 seconds to 33 seconds."
        )
        
        # Save the constructed script for reference
        project.constructed_prompt = prompt
        project.save()

        # Call HeyGen API
        client = HeyGenClient()
        response = client.generate_video_agent(prompt, avatar_id=project.avatar_id)
        
        # HeyGen returns: {"data": {"video_id": "..."}}
        video_id = response.get('data', {}).get('video_id')
        
        if not video_id:
            logger.error(f"HeyGen did not return a video_id. Response: {response}")
            project.status = VideoProject.Status.FAILED
            project.save()
            return "Failed to get video_id"

        project.heygen_video_id = video_id
        project.save()
        
        # Trigger monitoring task
        monitor_video_status_task.delay(project.id)
        
        return f"Started generation for project {project_id} (Video ID: {video_id})"

    except VideoProject.DoesNotExist:
        logger.error(f"VideoProject {project_id} does not exist.")
        return "Project not found"
    except Exception as e:
        logger.error(f"Generate Video Task Failed: {e}")
        if 'project' in locals():
            project.status = VideoProject.Status.FAILED
            project.save()
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=60)
def monitor_video_status_task(self, project_id):
    """
    Background task to monitor video status.
    Polls HeyGen API until completed or failed.
    """
    try:
        project = VideoProject.objects.get(id=project_id)
        
        # Stop if already done
        if project.status in [VideoProject.Status.COMPLETED, VideoProject.Status.FAILED]:
            return f"Project {project_id} already reached final status: {project.status}"

        if not project.heygen_video_id:
            # If no ID yet, wait and retry
            logger.warning(f"Project {project_id} has no HeyGen ID yet. Retrying...")
            raise self.retry(countdown=30)

        # Check HeyGen
        client = HeyGenClient()
        response = client.check_status(project.heygen_video_id)
        data = response.get('data', {})
        heygen_status = data.get('status')
        video_url = data.get('video_url') or data.get('url')
        
        logger.info(f"Checking status for {project_id}: {heygen_status}")

        if heygen_status == 'completed':
            from django.utils import timezone
            now = timezone.now()
            
            # Atomic update to prevent race conditions
            # Only update if status is NOT already COMPLETED
            rows_updated = VideoProject.objects.filter(
                id=project_id
            ).exclude(
                status=VideoProject.Status.COMPLETED
            ).update(
                status=VideoProject.Status.COMPLETED,
                video_url=video_url,
                completed_at=now,
                updated_at=now
            )
            
            if rows_updated > 0:
                # We successfully claimed the completion event
                project.refresh_from_db()
                
                # Send Email
                print(f"DEBUG: Video {project_id} completed. Attempting to send email...")
                from .utils import send_video_ready_email
                send_video_ready_email(project)
                
                return f"Video {project_id} completed and email sent."
            else:
                 return f"Video {project_id} already marked completed by another process."

        elif heygen_status == 'failed':
            project.status = VideoProject.Status.FAILED
            project.save()
            return f"Video {project_id} failed generation."
            
        else:
            # Still processing/pending -> Retry in 30s
            raise self.retry(countdown=30)
            
    except VideoProject.DoesNotExist:
        return "Project not found"
    except Exception as e:
        logger.error(f"Error monitoring video {project_id}: {e}")
        raise self.retry(exc=e, countdown=60)
