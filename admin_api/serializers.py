from rest_framework import serializers
from accounts.models import CustomUser
from videogen.models import VideoProject

class AdminUserSerializer(serializers.ModelSerializer):
    total_videos = serializers.SerializerMethodField()
    failed_videos = serializers.SerializerMethodField()
    generated_scripts = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'username', 'is_active', 'is_staff', 'is_superuser', 
            'is_email_verified', 'auth_provider', 'admin_permissions', 'date_joined', 'last_login',
            'total_videos', 'failed_videos', 'generated_scripts'
        )

    def get_total_videos(self, obj):
        return obj.video_projects.count()

    def get_failed_videos(self, obj):
        return obj.video_projects.filter(status='video_failed').count()

    def get_generated_scripts(self, obj):
        from django.db.models import Q
        return obj.video_projects.filter(
            ~Q(generated_script='') | ~Q(finalized_script='')
        ).count()


class AdminVideoProjectSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    video_file_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoProject
        fields = (
            # Identity
            'id',
            # User
            'user_id', 'user_email', 'user_username',
            # Core content
            'title', 'industry', 'background', 'service_description',
            # Avatar
            'avatar_id', 'avatar_name', 'avatar_gender', 'avatar_outfit',
            'avatar_preview_url', 'avatar_preview_video_url',
            # Scripts
            'generated_script', 'finalized_script',
            # Video output — use video_file_url (stored file) not video_url (HeyGen CDN)
            'heygen_video_id', 'video_file_url', 'video_status_message',
            # Status & timestamps
            'status', 'created_at', 'updated_at',
        )

    def get_video_file_url(self, obj):
        """Return absolute URL of the locally-stored video file."""
        if not obj.video_file:
            return None
        from django.conf import settings
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.video_file.url)
        backend = getattr(settings, 'BACKEND_URL', 'http://localhost:8000').rstrip('/')
        return f"{backend}{obj.video_file.url}"
