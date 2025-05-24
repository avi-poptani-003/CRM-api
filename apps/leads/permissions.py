from rest_framework import permissions

class IsOwnerOrAssignedOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return self._check_permissions(request, obj)

    def has_permission(self, request, view):
        # For list/create operations, just check if user is authenticated
        if view.action in ['list', 'create']:
            return request.user and request.user.is_authenticated
            
        # For other actions, check if user would have object permission
        # Object will be checked in has_object_permission if it exists
        return request.user and request.user.is_authenticated

    def _check_permissions(self, request, obj=None):
        user = request.user
        
        # Allow any authenticated request if user is admin/superuser
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            return True
            
        # Managers can access all leads
        if getattr(user, 'role', None) == 'manager':
            return True
            
        # Agents/regular users can only access leads assigned to them
        if obj is None:  # No specific object to check (e.g. during list)
            return True
        return obj.assigned_to == user