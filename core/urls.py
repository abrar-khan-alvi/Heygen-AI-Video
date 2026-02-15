"""
URL Configuration for core project.

This file sets up:
1. Admin URLs
2. API versioning with /api/v1/ prefix
3. Includes accounts app URLs

Note: Using simple path prefix instead of regex group to avoid
passing version as kwarg to views. DRF versioning is handled
via request.version in the views.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/videos/', include('videos.urls')),
]
