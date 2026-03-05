from django.urls import path
from . import views

app_name = "videogen"

urlpatterns = [
    # ── Options (no auth, instant from DB) ──────────────────────────────
    path("options/industries/", views.IndustryListView.as_view(), name="industry-list"),
    path("options/backgrounds/", views.BackgroundListView.as_view(), name="background-list"),
    path("options/avatars/", views.AvatarBrowseView.as_view(), name="avatar-browse"),
    path("options/avatars/<str:avatar_id>/", views.AvatarDetailView.as_view(), name="avatar-detail"),

    # ── Project flow ────────────────────────────────────────────────────
    # Screen 1: Create draft
    path("projects/create/", views.ProjectCreateView.as_view(), name="project-create"),

    # Screens 2-4: Update draft (PATCH any fields)
    path("projects/<uuid:project_id>/update/", views.ProjectUpdateView.as_view(), name="project-update"),

    # Screen 5: Generate script
    path("projects/<uuid:project_id>/generate-script/", views.ScriptGenerateView.as_view(), name="script-generate"),

    # Screen 6: Finalize script
    path("projects/<uuid:project_id>/finalize-script/", views.ScriptFinalizeView.as_view(), name="script-finalize"),

    # Screen 7: Generate video
    path("projects/<uuid:project_id>/generate-video/", views.VideoGenerateView.as_view(), name="video-generate"),

    # Screen 8: Poll video status
    path("projects/<uuid:project_id>/video-status/", views.VideoStatusView.as_view(), name="video-status"),

    # ── Project list & detail ───────────────────────────────────────────
    path("projects/", views.ProjectListView.as_view(), name="project-list"),
    path("projects/<uuid:project_id>/", views.ProjectDetailView.as_view(), name="project-detail"),
]