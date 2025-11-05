# core/context_processors.py
from .models import TaskApplication, Notification

def notification_count(request):
    if request.user.is_authenticated:
        # Count applications for user's posts
        unread_applications = TaskApplication.objects.filter(
            post__user=request.user,
            post__status='approved', 
            post__task_status='open'
        ).count()
        
        # Count unread notifications
        unread_notifications = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).count()
        
        return {
            'unread_notifications_count': unread_notifications,
            'unread_applications_count': unread_applications
        }
    return {}