from django.urls import path
from django.db import models
from . import views

urlpatterns = [
    path('stats/dashboard/', views.DashboardStatsView.as_view(), name='admin-dashboard-stats'),
    path('profile/change-password/', views.AdminChangePasswordView.as_view(), name='admin-change-password'),
    path('users/', views.AdminUserListView.as_view(), name='admin-user-list'),
    path('users/<uuid:pk>/', views.AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('staff/', views.AdminStaffListView.as_view(), name='admin-staff-list'),
    path('staff/create/', views.AdminCreateStaffView.as_view(), name='admin-staff-create'),
    path('staff/<uuid:pk>/', views.AdminDeleteStaffView.as_view(), name='admin-staff-delete'),
    path('staff/<uuid:pk>/permissions/', views.AdminUpdateStaffPermissionsView.as_view(), name='admin-staff-update-permissions'),
    path('videos/', views.AdminVideoListView.as_view(), name='admin-video-list'),
    path('videos/<uuid:pk>/', views.AdminVideoDetailView.as_view(), name='admin-video-detail'),
]
