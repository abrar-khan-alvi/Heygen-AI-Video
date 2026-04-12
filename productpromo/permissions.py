from rest_framework import permissions

class IsPromoProjectOwner(permissions.BasePermission):
    """
    Object-level permission to only allow owners of a project to edit/view it.
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
