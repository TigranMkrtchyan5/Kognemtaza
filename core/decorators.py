from django.shortcuts import redirect
from django.contrib import messages

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_superuser or request.user.profile.role == "admin"):
            return view_func(request, *args, **kwargs)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')
    return wrapper

def moderator_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and (
            request.user.is_superuser or 
            request.user.profile.role == "admin" or
            request.user.profile.role == "moderator"
        ):
            return view_func(request, *args, **kwargs)
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')
    return wrapper
