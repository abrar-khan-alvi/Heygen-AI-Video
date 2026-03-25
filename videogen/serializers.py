from rest_framework import serializers
from django.conf import settings
from .models import VideoProject, Industry, Background, CachedAvatar, CachedVoice


def _build_media_url(relative_url, request=None):
    """Build an absolute URL for a media file.

    Priority:
    1. Use request.build_absolute_uri() if available — honours
       X-Forwarded-Host / X-Forwarded-Proto set by the reverse proxy.
    2. Fallback to BACKEND_URL from settings (set in .env for production).
    """
    if request:
        return request.build_absolute_uri(relative_url)
    backend = getattr(settings, 'BACKEND_URL', 'http://localhost:8000').rstrip('/')
    return f"{backend}{relative_url}"


# ─── Option serializers ─────────────────────────────────────────────────────

class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = ["id", "name", "icon"]


class BackgroundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Background
        fields = ["id", "name", "description", "icon"]


class CachedAvatarSerializer(serializers.ModelSerializer):
    suggested_voice_id = serializers.SerializerMethodField()
    suggested_voice = serializers.SerializerMethodField()

    class Meta:
        model = CachedAvatar
        fields = [
            "avatar_id", "avatar_name", "gender",
            "outfit_category", "pose", "angle",
            "preview_image_url", "preview_video_url",
            "default_voice_id", "suggested_voice_id", "suggested_voice",
        ]

    def get_suggested_voice_id(self, obj):
        voice = obj.get_suggested_voice()
        return voice.voice_id if voice else ""

    def get_suggested_voice(self, obj):
        voice = obj.get_suggested_voice()
        if voice:
            return CachedVoiceSerializer(voice).data
        return None


class CachedVoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CachedVoice
        fields = ["voice_id", "name", "language", "language_code", "gender", "preview_audio_url"]


# ─── Project serializers ────────────────────────────────────────────────────

class ProjectCreateSerializer(serializers.Serializer):
    """Screen 1: Create draft with industry."""
    industry = serializers.CharField(max_length=200)


class ProjectPatchSerializer(serializers.Serializer):
    """
    PATCH — update any field(s). All optional.
    Frontend sends only the fields being changed on each screen.
    """
    # Screen 2
    title = serializers.CharField(max_length=255, required=False)
    service_description = serializers.CharField(required=False)

    # Screen 3
    background = serializers.CharField(max_length=500, required=False)

    # Screen 4
    avatar_id = serializers.CharField(max_length=255, required=False)
    voice_id = serializers.CharField(max_length=255, required=False, allow_blank=True)

    # Also allow re-updating industry (if user goes back)
    industry = serializers.CharField(max_length=200, required=False)


class ScriptFinalizeSerializer(serializers.Serializer):
    finalized_script = serializers.CharField()


class VideoProjectSerializer(serializers.ModelSerializer):
    video_file_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoProject
        fields = [
            "id", "title", "industry", "service_description", "background",
            "avatar_id", "avatar_name", "avatar_gender", "avatar_outfit",
            "avatar_preview_url", "avatar_preview_video_url", "voice_id",
            "generated_script", "finalized_script",
            "heygen_video_id", "video_url", "video_file_url",
            "video_status_message",
            "status", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_video_file_url(self, obj):
        if obj.video_file:
            request = self.context.get("request")
            return _build_media_url(obj.video_file.url, request)
        return None


class VideoProjectListSerializer(serializers.ModelSerializer):
    video_file_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoProject
        fields = [
            "id", "title", "industry", "status",
            "avatar_name", "avatar_outfit",
            "video_file_url", "created_at",
        ]

    def get_video_file_url(self, obj):
        if obj.video_file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.video_file.url)
            return obj.video_file.url
        return None