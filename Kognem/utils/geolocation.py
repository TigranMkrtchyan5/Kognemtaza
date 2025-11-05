import requests
import logging

logger = logging.getLogger(__name__)

def get_geolocation(ip_address):
    """Get geolocation data from IP address"""
    try:
        # TEMPORARILY COMMENT THIS OUT FOR TESTING:
        # if ip_address in ['127.0.0.1', 'localhost'] or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
        #     return {'country': 'Local', 'city': 'Local'}
            
        # Using ipapi.co (free tier available)
        response = requests.get(f'http://ipapi.co/{ip_address}/json/', timeout=5)
        data = response.json()
        return {
            'country': data.get('country_name', 'Unknown'),
            'city': data.get('city', 'Unknown')
        }
    except Exception as e:
        logger.error(f"Error getting geolocation for {ip_address}: {e}")
        return {'country': 'Unknown', 'city': 'Unknown'}

def get_client_ip(request):
    """Get client IP address"""
    try:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
    except Exception as e:
        logger.error(f"Error getting client IP: {e}")
        return '0.0.0.0'