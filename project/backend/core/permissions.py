from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))


class IsEngineer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and hasattr(request.user, 'engineer_profile') and request.user.engineer_profile.active)


class IsAdminOrEngineer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and ((request.user.is_staff or request.user.is_superuser) or hasattr(request.user, 'engineer_profile')))
