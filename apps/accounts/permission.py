from rest_framework import permissions

class IsAdmin(permissions.BasePermission): 
    """
    Permission check for admin users 
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin()

class IsManager(permissions.BasePermission):
    """
    Permission check for manager users
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_admin() or request.user.is_manager()
        )

class IsAgentOrAbove(permissions.BasePermission):
    """
    Permission check for agent or above users
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated