from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone




# ---------------- User Activity ----------------
class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action[:30]}"

# ---------------- Ban Log ----------------

class BanLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bans")
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="issued_bans")
    reason = models.TextField()
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    active = models.BooleanField(default=True)  # optional for historical tracking

    @property
    def is_active(self):
        """Return True if ban is currently active"""
        return timezone.now() < self.end_date

    def __str__(self):
        admin_name = self.admin.username if self.admin else "System"
        return f"{self.user.username} banned by {admin_name}"

# ---------------- Profil ----------------
class Profile(models.Model):
    ROLE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('admin', 'Admin'),
        ('support', 'Support'),
        ('user', 'User'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    verification_id = models.CharField(max_length=50, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return self.full_name if self.full_name else self.user.username

    @property
    def is_banned(self):
        return self.user.bans.filter(end_date__gt=timezone.now()).exists()

# ---------------- Post Model ----------------
class Post(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    title = models.CharField(max_length=255, default='')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    image = models.ImageField(upload_to='posts/')
    description = models.TextField()
    location = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # НОВОЕ ПОЛЕ: Для хранения причины отказа
    rejection_reason = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"
# ---------------- Admin Inline for Profile ----------------
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

# ---------------- Custom User Admin ----------------
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'get_full_name', 'get_phone', 'get_verification_id', 'get_role', 'is_banned', 'is_staff', 'is_active', 'date_joined')
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

    def get_role(self, instance):
        return instance.profile.role if hasattr(instance, 'profile') else ''
    get_role.short_description = 'Role'

    def is_banned(self, instance):
        if hasattr(instance, 'profile'):
            return instance.profile.is_banned
        return False
    is_banned.boolean = True
    is_banned.short_description = 'Banned'

# ---------------- Register Admin ----------------
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('user', 'description', 'location', 'price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('description', 'location', 'user__username')
