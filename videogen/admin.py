from django.contrib import admin
from .models import Industry, Background, CachedAvatar, VideoProject


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ["name", "icon", "is_active", "sort_order"]
    list_editable = ["is_active", "sort_order", "icon"]
    list_filter = ["is_active"]
    search_fields = ["name"]


@admin.register(Background)
class BackgroundAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "icon", "is_active", "sort_order"]
    list_editable = ["is_active", "sort_order", "icon"]
    list_filter = ["is_active"]
    search_fields = ["name"]


@admin.register(CachedAvatar)
class CachedAvatarAdmin(admin.ModelAdmin):
    list_display = [
        "avatar_name", "gender", "outfit_category",
        "pose", "angle", "is_active", "synced_at",
    ]
    list_editable = ["outfit_category", "is_active"]
    list_filter = ["gender", "outfit_category", "is_active"]
    search_fields = ["avatar_name", "avatar_id"]
    readonly_fields = ["avatar_id", "synced_at"]


@admin.register(VideoProject)
class VideoProjectAdmin(admin.ModelAdmin):
    list_display = [
        "id", "user", "title", "industry", "avatar_name",
        "status", "created_at",
    ]
    list_filter = ["status", "industry"]
    search_fields = ["title", "user__email", "user__username"]
    readonly_fields = ["id", "created_at", "updated_at"]