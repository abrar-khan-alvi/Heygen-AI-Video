"""
Admin configuration for accounts app.

This registers our custom models with Django Admin
so we can manage users through the admin interface.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Custom admin for CustomUser model.
    
    Extends Django's UserAdmin to work with our custom fields.
    """
    
    # Fields to display in the user list
    list_display = (
        'email', 
        'username', 
        'is_email_verified', 
        'auth_provider',
        'is_staff', 
        'date_joined'
    )
    
    # Fields to filter by in the sidebar
    list_filter = (
        'is_email_verified', 
        'auth_provider', 
        'is_staff', 
        'is_superuser', 
        'is_active'
    )
    
    # Fields to search by
    search_fields = ('email', 'username')
    
    # Default ordering
    ordering = ('-date_joined',)
    
    # Fieldsets for the user detail/edit page
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Verification', {'fields': ('is_email_verified', 'auth_provider')}),
        ('Social Auth', {'fields': ('google_id', 'apple_id')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Fieldsets for the add user page
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )


# =============================================================================
# HIDE TOKEN BLACKLIST
# =============================================================================

try:
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
    from django.contrib.admin.sites import NotRegistered
    
    admin.site.unregister(OutstandingToken)
    admin.site.unregister(BlacklistedToken)
except ImportError:
    pass
except NotRegistered:
    pass



