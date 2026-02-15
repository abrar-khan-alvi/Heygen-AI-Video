from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class VideoProject(models.Model):
    """
    Stores the user inputs and status of a HeyGen Video Agent project.
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
    
    class Gender(models.TextChoices):
        MALE = 'Male', 'Male'
        FEMALE = 'Female', 'Female'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_projects')
    
    # User Inputs
    title = models.CharField(max_length=255, blank=True, help_text="Project Title")
    industry = models.CharField(max_length=100, help_text="e.g. Real Estate, Healthcare")
    service_description = models.TextField(help_text="Description of the service or product")
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.FEMALE)
    background_type = models.CharField(max_length=100, help_text="e.g. Office, Gym, Studio")
    avatar_outfit = models.CharField(max_length=100, help_text="e.g. Business Suit, Casual, Doctor Coat")
    avatar_id = models.CharField(max_length=100, help_text="HeyGen Avatar ID", default="Abigail_expressive_2024112501")
    
    # System Fields
    constructed_prompt = models.TextField(blank=True, help_text="The full prompt sent to HeyGen")
    heygen_video_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID returned by HeyGen API")
    video_url = models.URLField(blank=True, null=True, help_text="Final video URL")
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title or self.industry} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f"{self.industry} Video - {self.created_at.strftime('%Y-%m-%d') if self.created_at else 'New'}"
        super().save(*args, **kwargs)
