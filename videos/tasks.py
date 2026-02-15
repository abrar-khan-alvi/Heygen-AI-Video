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

        # Construct the prompt from user inputs
        prompt = (
            f"Create a high-quality marketing video for the {project.industry} industry. "
            f"Service Description: {project.service_description}. "
            f"The presenter should be a {project.gender}. "
            f"The background should look like a {project.background_type}. "
            f"The presenter should be wearing a {project.avatar_outfit}. "
            f"Make it professional, engaging, and suitable for social media."
        )
        
        # Save the constructed prompt for reference
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
    Polls HeyGen for status. Retries up to 60 times (30 mins).
    """
    """
    Polls HeyGen for video status until completion or failure.
    """
    try:
        project = VideoProject.objects.get(id=project_id)
        
        if not project.heygen_video_id:
            logger.error(f"Project {project_id} has no heygen_video_id.")
            return "No Video ID"

        client = HeyGenClient()
        response = client.check_status(project.heygen_video_id)
        
        # Response format depends on endpoint, assuming:
        # {"data": {"status": "completed", "video_url": "..."}}
        data = response.get('data', {})
        status = data.get('status')
        video_url = data.get('video_url') or data.get('url')
        
        logger.info(f"Checking status for {project.heygen_video_id}: {status}")

        if status == 'completed':
            project.status = VideoProject.Status.COMPLETED
            project.video_url = video_url
            project.save()
            return f"Video {project_id} completed!"
            
        elif status == 'failed':
            project.status = VideoProject.Status.FAILED
            project.save()
            return f"Video {project_id} failed remotely."
            
        else:
            # Still processing (pending, processing, etc.)
            # Retry in 30 seconds
            raise self.retry(countdown=30)

    except VideoProject.DoesNotExist:
        return "Project not found"
    except Exception as e:
        logger.error(f"Monitor Task Failed: {e}")
        raise self.retry(exc=e, countdown=60)
