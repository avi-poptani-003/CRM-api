from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to admin users (superuser or role='admin').
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and \
                    (request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'))

class IsManagerUser(permissions.BasePermission):
    """
    Allows access only to manager users (role='manager').
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and \
                    getattr(request.user, 'role', None) == 'manager')

class IsAdminOrManagerUser(permissions.BasePermission):
    """
    Allows access only to admin or manager users.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return bool(request.user.is_superuser or \
                    getattr(request.user, 'role', None) in ['admin', 'manager'])

class IsOwnerOrAssignedOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object, users assigned to it,
    or admin/manager users to interact with it.
    Managers and Admins have full access to all leads.
    Agents can only access leads assigned to them.
    """
    def has_object_permission(self, request, view, obj):
        # Admin and Manager users have full object permissions
        if request.user.is_superuser or \
           getattr(request.user, 'role', None) in ['admin', 'manager']:
            return True
        
        # Check if the user is the one assigned to the lead
        return obj.assigned_to == request.user

    def has_permission(self, request, view):
        # This check is for list/create views or actions not tied to a specific object yet.
        # Allow if authenticated. Object-specific checks are in has_object_permission.
        # For actions like 'list', the queryset filtering in get_queryset handles role-based access.
        return bool(request.user and request.user.is_authenticated)


