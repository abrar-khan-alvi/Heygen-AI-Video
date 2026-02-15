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
            f"The presenter is a {project.gender}. " # Changed from "should be" to "is" to be more declarative
            f"The background is a {project.background_type}. "
            f"The presenter is wearing {project.avatar_outfit} attire. "
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
        # UPDATED: We disabled auto-monitoring to save resources. 
        # Status will be checked on-demand when the user views the project.
        # monitor_video_status_task.delay(project.id)
        
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
    DEPRECATED: Background monitoring is disabled in favor of on-demand checks.
    Refer to videos/views.py -> VideoProjectDetailView.retrieve()
    """
    return "Monitoring disabled."
    # Original logic commented out below:
    # try:
    #     project = VideoProject.objects.get(id=project_id)
    # ...
