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

from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)
class BanCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Проверяем и обновляем баны ДО обработки запроса
        if request.user.is_authenticated:
            self._update_expired_bans(request.user)
            
            # Проверяем активные баны
            active_ban = self._get_active_ban(request.user)
            if active_ban:
                # Не блокируем админ-панель для администраторов
                if (request.path.startswith('/admin/') and 
                    hasattr(request.user, 'profile') and 
                    request.user.profile.role in ['admin', 'superadmin']):
                    return self.get_response(request)
                
                # Разлогиниваем и редиректим забаненного пользователя
                from django.contrib.auth import logout
                logout(request)
                
                # Форматируем время для сообщения
                local_time = timezone.localtime(active_ban.end_date)
                messages.error(
                    request,
                    f"Your account is banned until {local_time.strftime('%Y-%m-%d %H:%M')}. Reason: {active_ban.reason}"
                )
                logger.warning(f"Banned user {request.user.username} attempted to access {request.path}")
                
                # Редирект на логин
                from django.shortcuts import redirect
                response = redirect('login')
                return response
        
        # Продолжаем нормальную обработку запроса
        response = self.get_response(request)
        return response

    def _update_expired_bans(self, user):
        """Обновляем просроченные баны и активируем пользователей"""
        now = timezone.now()
        expired_bans = user.bans.filter(active=True, end_date__lte=now)
        
        if expired_bans.exists():
            expired_count = expired_bans.count()
            expired_bans.update(active=False)
            logger.info(f"Updated {expired_count} expired bans for user {user.username}")
            
            # Проверяем есть ли другие активные баны
            active_bans_count = user.bans.filter(active=True, end_date__gt=now).count()
            if active_bans_count == 0 and not user.is_active:
                user.is_active = True
                user.save()
                logger.info(f"Reactivated user {user.username} after ban expiration")

    def _get_active_ban(self, user):
        """Получаем активный бан пользователя"""
        now = timezone.now()
        return user.bans.filter(active=True, end_date__gt=now).first()