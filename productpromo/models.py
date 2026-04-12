import uuid
from django.db import models
from django.conf import settings

class ProductPromoProject(models.Model):
    """
    Model for standalone product promotional videos.
    Completely isolated from the main videogen app.
    """
    class StatusChoice(models.TextChoices):
        DRAFT            = "draft",            "Draft"
        SCRIPT_GENERATED = "script_generated", "Script Generated"
        SCRIPT_FINALIZED = "script_finalized", "Script Finalized"
        VIDEO_PROCESSING = "video_processing", "Video Processing"
        VIDEO_COMPLETED  = "video_completed",  "Video Completed"
        VIDEO_FAILED     = "video_failed",     "Video Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_promo_projects",
    )

    # ── Product Info ──────────────────────────────────────────────────────────
    product_name        = models.CharField(max_length=255)
    product_description = models.TextField()
    product_image       = models.ImageField(
        upload_to="product_promo/images/%Y/%m/",
        blank=True,
        null=True,
    )

    # ── AI Script ─────────────────────────────────────────────────────────────
    generated_script = models.TextField(blank=True, default="")
    finalized_script = models.TextField(blank=True, default="")

    # ── HeyGen Configuration ──────────────────────────────────────────────────
    avatar_id     = models.CharField(max_length=255, blank=True, default="")
    avatar_name   = models.CharField(max_length=255, blank=True, default="")
    avatar_gender = models.CharField(max_length=20,  blank=True, default="")
    avatar_preview_url = models.URLField(max_length=1000, blank=True, default="")
    
    voice_id      = models.CharField(max_length=255, blank=True, default="")

    # ── Video Info ────────────────────────────────────────────────────────────
    heygen_video_id      = models.CharField(max_length=255, blank=True, db_index=True)
    video_url            = models.URLField(max_length=1000, blank=True, default="")
    video_file           = models.FileField(
        upload_to="product_promo/videos/%Y/%m/",
        blank=True,
        null=True,
    )
    video_status_message = models.TextField(blank=True, default="")

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=30,
        choices=StatusChoice.choices,
        default=StatusChoice.DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product_name} — {self.user}"
