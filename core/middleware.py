# core/middleware.py
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

# Cookie names
USER_SESSION_COOKIE = getattr(settings, "USER_SESSION_COOKIE_NAME", "user_sessionid")
ADMIN_SESSION_COOKIE = getattr(settings, "ADMIN_SESSION_COOKIE_NAME", "admin_sessionid")

class AdminSessionMiddleware(MiddlewareMixin):
    """
    Middleware that switches the session cookie name depending on request path.
    If the path begins with the admin path prefix (/staff-panel/), we temporarily
    set settings.SESSION_COOKIE_NAME to the admin cookie name so Django's
    SessionMiddleware will read/write that cookie.
    """

    admin_prefixes = getattr(settings, "ADMIN_URL_PREFIXES", ["/staff-panel/"])

    def process_request(self, request):
        # Save original so we can restore later
        request._original_session_cookie_name = getattr(settings, "SESSION_COOKIE_NAME", USER_SESSION_COOKIE)
        # If this is an admin request, set the cookie name to admin cookie
        path = request.path or ""
        if any(path.startswith(pref) for pref in self.admin_prefixes):
            settings.SESSION_COOKIE_NAME = ADMIN_SESSION_COOKIE
        else:
            settings.SESSION_COOKIE_NAME = USER_SESSION_COOKIE

    def process_response(self, request, response):
        # Ensure we set the cookie names back when returning response
        # (restore original SESSION_COOKIE_NAME)
        original = getattr(request, "_original_session_cookie_name", USER_SESSION_COOKIE)
        settings.SESSION_COOKIE_NAME = original
        return response



# middleware/ban_middleware.py
from django.shortcuts import redirect
from django.contrib.auth import logout



