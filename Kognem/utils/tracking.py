# utils/tracking.py

from .device_fingerprint import generate_device_fingerprint, parse_user_agent
from .geolocation import get_geolocation, get_client_ip
from models import UserLoginHistory

def track_user_action(user, request, action_type):
    """Track important user actions"""
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    device_fingerprint = generate_device_fingerprint(request)
    device_info = parse_user_agent(user_agent)
    geolocation = get_geolocation(ip_address)
    
    UserLoginHistory.objects.create(
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        device_fingerprint=device_fingerprint,
        browser=device_info['browser'],
        os=device_info['os'],
        device_type=device_info['device_type'],
        country=geolocation['country'],
        city=geolocation['city'],
        action_type=action_type  # You might want to add this field to your model
    )