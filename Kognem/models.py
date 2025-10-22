from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# Profile model for extra fields
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, blank=True)  # Added full_name
    phone = models.CharField(max_length=20, blank=True)
    verification_id = models.CharField(max_length=50, blank=True)

    def __str__(self):
        # Display full_name if available, fallback to username
        return self.full_name if self.full_name else self.user.username


# Admin inline to display Profile inside User admin
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


# Custom UserAdmin
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'get_full_name', 'get_phone', 'get_verification_id', 'is_staff', 'is_active', 'date_joined')
    list_select_related = ('profile',)

    def get_full_name(self, instance):
        return instance.profile.full_name if hasattr(instance, 'profile') else ''
    get_full_name.short_description = 'Full Name'

    def get_phone(self, instance):
        return instance.profile.phone if hasattr(instance, 'profile') else ''
    get_phone.short_description = 'Phone'

    def get_verification_id(self, instance):
        return instance.profile.verification_id if hasattr(instance, 'profile') else ''
    get_verification_id.short_description = 'Verification ID'


# Unregister default User and register custom UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
