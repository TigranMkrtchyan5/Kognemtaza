from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q

class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(Q(username=username) | Q(email=username))
        except User.DoesNotExist:
            return None

        if user.check_password(password):
            return user
        return None
    
    # core/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.utils import timezone

class BanCheckBackend(ModelBackend):
    """
    Extends Django ModelBackend to prevent banned users from authenticating.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user:
            # If user has an active ban, reject authentication
            if user.bans.filter(active=True, end_date__gt=timezone.now()).exists():
                return None
        return user
