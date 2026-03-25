import uuid
from django.db import models
from django.conf import settings


# ═══════════════════════════════════════════════════════════════════════════════
# OPTION TABLES
# ═══════════════════════════════════════════════════════════════════════════════

class Industry(models.Model):
    name = models.CharField(max_length=200, unique=True)
    icon = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Industries"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Background(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.CharField(
        max_length=500, blank=True,
        help_text="Detailed description passed to Video Agent prompt",
    )
    icon = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


# ═══════════════════════════════════════════════════════════════════════════════
# CACHED AVATAR
# ═══════════════════════════════════════════════════════════════════════════════

class CachedAvatar(models.Model):
    class GenderChoice(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    class OutfitCategory(models.TextChoices):
        BUSINESS = "business", "Business"
        CASUAL = "casual", "Casual"
        FORMAL = "formal", "Formal"
        HEALTHCARE = "healthcare", "Healthcare"
        OUTDOOR = "outdoor", "Outdoor"

    avatar_id = models.CharField(max_length=255, unique=True)
    avatar_name = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, choices=GenderChoice.choices, db_index=True)
    outfit_category = models.CharField(
        max_length=20, choices=OutfitCategory.choices, db_index=True,
        help_text="Admin can change if auto-detection was wrong",
    )
    pose = models.CharField(max_length=100, blank=True)
    angle = models.CharField(max_length=100, blank=True)
    preview_image_url = models.URLField(blank=True)
    preview_video_url = models.URLField(blank=True)
    default_voice_id = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["avatar_name", "outfit_category"]
        indexes = [
            models.Index(
                fields=["outfit_category", "is_active"],
                name="idx_avatar_outfit_active",
            ),
        ]

    def __str__(self):
        return f"{self.avatar_name} ({self.gender}, {self.outfit_category})"

    def save(self, *args, **kwargs):
        # Auto-populate default_voice_id if blank
        if not self.default_voice_id:
            suggested = self.get_suggested_voice()
            if suggested:
                self.default_voice_id = suggested.voice_id
        super().save(*args, **kwargs)

    def get_suggested_voice(self):
        """
        Returns a CachedVoice object based on:
        1. default_voice_id if set and exists in CachedVoice.
        2. First active voice where name matches avatar_name (case-insensitive) AND gender matches.
        3. Fallback: First active English voice (language_code starts with 'en') matching gender.
        """
        # 1. Default
        if self.default_voice_id:
            voice = CachedVoice.objects.filter(voice_id=self.default_voice_id, is_active=True).first()
            if voice:
                return voice

        # 2. Name match (case-insensitive) + Gender
        voice = CachedVoice.objects.filter(
            name__iexact=self.avatar_name,
            gender=self.gender,
            is_active=True
        ).first()
        if voice:
            return voice

        # 3. Fallback (First English + Gender)
        return CachedVoice.objects.filter(
            models.Q(language_code__istartswith="en") | models.Q(language__iexact="English"),
            gender=self.gender,
            is_active=True
        ).first()


# ═══════════════════════════════════════════════════════════════════════════════
# CACHED VOICE
# ═══════════════════════════════════════════════════════════════════════════════

class CachedVoice(models.Model):
    """Stores the HeyGen voice library fetched from /v2/voices."""
    voice_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    language = models.CharField(max_length=100, blank=True, default="")
    language_code = models.CharField(max_length=20, blank=True, default="")
    gender = models.CharField(max_length=10, blank=True, default="")
    preview_audio_url = models.URLField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["language", "name"]

    def __str__(self):
        return f"{self.name} ({self.language}, {self.gender})"


# ═══════════════════════════════════════════════════════════════════════════════
# VIDEO PROJECT (draft-based, built step by step)
# ═══════════════════════════════════════════════════════════════════════════════

class VideoProject(models.Model):
    class StatusChoice(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCRIPT_GENERATED = "script_generated", "Script Generated"
        SCRIPT_FINALIZED = "script_finalized", "Script Finalized"
        VIDEO_PROCESSING = "video_processing", "Video Processing"
        VIDEO_COMPLETED = "video_completed", "Video Completed"
        VIDEO_FAILED = "video_failed", "Video Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="video_projects",
        db_index=True,
    )

    # Screen 1: Industry
    industry = models.CharField(max_length=200, blank=True, default="")

    # Screen 2: Title + Service Description
    title = models.CharField(max_length=255, blank=True, default="")
    service_description = models.TextField(blank=True, default="")

    # Screen 3: Background
    background = models.CharField(max_length=500, blank=True, default="")

    # Screen 4: Avatar (gender auto-detected from CachedAvatar)
    avatar_id = models.CharField(max_length=255, blank=True, default="")
    avatar_name = models.CharField(max_length=255, blank=True, default="")
    avatar_gender = models.CharField(max_length=10, blank=True, default="")
    avatar_outfit = models.CharField(max_length=200, blank=True, default="")
    avatar_preview_url = models.URLField(blank=True, default="")
    avatar_preview_video_url = models.URLField(blank=True, default="")
    voice_id = models.CharField(max_length=255, blank=True, default="")

    # Script
    generated_script = models.TextField(blank=True, default="")
    finalized_script = models.TextField(blank=True, default="")

    # Video
    heygen_video_id = models.CharField(max_length=255, blank=True, db_index=True)
    video_url = models.URLField(blank=True, default="")
    video_file = models.FileField(upload_to="videos/%Y/%m/", blank=True, null=True)
    video_status_message = models.TextField(blank=True, default="")

    # Meta
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
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_project_user_date"),
            models.Index(fields=["user", "status"], name="idx_project_user_status"),
        ]

    def __str__(self):
        return f"[{self.status}] {self.title or 'Untitled'} — {self.user}"