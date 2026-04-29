from django.contrib.auth.models import update_last_login
from django.utils import timezone


class SessionExpiryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        # Only apply to authenticated staff users on panel/admin routes
        if user and user.is_authenticated and user.is_staff:
            if hasattr(user, 'last_login') and user.last_login:
                # Expire session after 8 hours of inactivity
                if (timezone.now() - user.last_login).total_seconds() > 8 * 3600:
                    from django.contrib.auth import logout
                    logout(request)

        response = self.get_response(request)
        return response
