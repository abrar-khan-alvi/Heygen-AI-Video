from django.urls import path
from .views import VideoProjectListCreateView, VideoProjectDetailView, AvatarListView, VideoStatusView, GenerateScriptView

urlpatterns = [
    path('projects/', VideoProjectListCreateView.as_view(), name='video-list-create'),
    path('projects/<uuid:id>/', VideoProjectDetailView.as_view(), name='video-detail'),
    path('projects/<uuid:id>/status/', VideoStatusView.as_view(), name='video-status'),
    path('avatars/', AvatarListView.as_view(), name='avatar-list'),
    path('generate-script/', GenerateScriptView.as_view(), name='generate-script'),
]
