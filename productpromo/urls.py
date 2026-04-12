from django.urls import path
from . import views

urlpatterns = [
    path("projects/", views.PromoProjectCreateView.as_view(), name="project-create"),
    path("projects/list/", views.PromoProjectListView.as_view(), name="project-list"),
    path("projects/<uuid:project_id>/", views.PromoProjectDetailView.as_view(), name="project-detail"),
    path("projects/<uuid:project_id>/update/", views.PromoProjectUpdateView.as_view(), name="project-update"),
    path("projects/<uuid:project_id>/upload-image/", views.PromoImageUploadView.as_view(), name="upload-image"),
    path("projects/<uuid:project_id>/generate-script/", views.PromoScriptGenerateView.as_view(), name="generate-script"),
    path("projects/<uuid:project_id>/finalize-script/", views.PromoScriptFinalizeView.as_view(), name="finalize-script"),
    path("projects/<uuid:project_id>/generate-video/", views.PromoVideoGenerateView.as_view(), name="generate-video"),
    path("projects/<uuid:project_id>/video-status/", views.PromoVideoStatusView.as_view(), name="video-status"),
]
