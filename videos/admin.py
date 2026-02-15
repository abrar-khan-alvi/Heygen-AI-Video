from django.contrib import admin
from .models import VideoProject

@admin.register(VideoProject)
class VideoProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'created_at', 'completed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'industry', 'user__email', 'heygen_video_id')
    readonly_fields = ('heygen_video_id', 'constructed_prompt', 'video_url', 'created_at', 'updated_at', 'completed_at')
