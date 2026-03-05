from rest_framework.permissions import BasePermission


class IsProjectOwner(BasePermission):
    """Check that the requesting user owns the project."""
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user