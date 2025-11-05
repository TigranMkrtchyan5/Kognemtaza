import hashlib
import logging

logger = logging.getLogger(__name__)

try:
    from user_agents import parse
except ImportError:
    logger.error("user_agents package not installed. Run: pip install django-user-agents")
    # Fallback function
    def parse(user_agent_string):
        return {
            'browser': 'Unknown',
            'os': 'Unknown', 
            'device_type': 'Unknown'
        }

def generate_device_fingerprint(request):
    """Generate a unique fingerprint for the user's device"""
    try:
        components = [
            request.META.get('HTTP_USER_AGENT', ''),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            request.META.get('HTTP_ACCEPT_ENCODING', ''),
            request.META.get('REMOTE_ADDR', ''),
        ]
        
        fingerprint_string = '|'.join(components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    except Exception as e:
        logger.error(f"Error generating device fingerprint: {e}")
        return "error_fingerprint"

def parse_user_agent(user_agent_string):
    """Parse user agent string to get device details"""
    try:
        user_agent = parse(user_agent_string)
        
        return {
            'browser': f"{user_agent.browser.family} {user_agent.browser.version_string}".strip(),
            'os': f"{user_agent.os.family} {user_agent.os.version_string}".strip(),
            'device_type': 'Mobile' if user_agent.is_mobile else 'Tablet' if user_agent.is_tablet else 'Desktop'
        }
    except Exception as e:
        logger.error(f"Error parsing user agent: {e}")
        return {
            'browser': 'Unknown',
            'os': 'Unknown',
            'device_type': 'Unknown'
        }