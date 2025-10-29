from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.contrib import admin






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
class Category(models.Model):
    name = models.CharField(max_length=100)
    

    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name


class State(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Province(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='provinces')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('state', 'name')

    def __str__(self):
        return f"{self.name} ({self.state.name})"
# Update Post
class Post(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    title = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    image = models.ImageField(upload_to='posts/')
    description = models.TextField()
    location = models.CharField(max_length=255)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True)
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.title} - {self.category.name if self.category else 'No Category'}"




class Logo(models.Model):
    logo = models.ImageField(upload_to='logo/')

    def __str__(self):
        return 'logo'

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





# class Room(models.Model):
#     room_name = models.CharField(max_length=255)

#     def __str__(self):
#         return self.room_name
    

# class Message(models.Model):
#     room = models.ForeignKey(Room, on_delete=models.CASCADE) 
#     sender = models.CharField(max_length=255)
#     message = models.TextField()    


#     def __str__(self):
#         return str(self.room) 




class Room(models.Model):
    """Represents a chat room between two users."""
    name = models.CharField(max_length=255, unique=True)
    users = models.ManyToManyField(User, related_name='rooms')

    def __str__(self):
        return self.name

class ChatMessage(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def to_dict(self):
        return {
            'id': self.id,
            'sender': self.sender.username,
            'recipient': self.recipient.username,
            'content': self.content,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
            
        }
    


# ---------------- Inline for ChatMessage ----------------
class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    fields = ('sender', 'recipient', 'short_content', 'created_at')
    readonly_fields = ('sender', 'recipient', 'short_content', 'created_at')
    extra = 0
    ordering = ('created_at',)

    def short_content(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    short_content.short_description = 'Message'

# ---------------- Room Admin ----------------
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'display_users', 'last_message_time')
    search_fields = ('users__username',)
    inlines = [ChatMessageInline]
    ordering = ('-id',)

    def display_users(self, obj):
        # Show participants' usernames separated by &
        return " & ".join([user.username for user in obj.users.all()])
    display_users.short_description = 'Participants'

    def last_message_time(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        return last_msg.created_at if last_msg else None
    last_message_time.admin_order_field = 'messages__created_at'
    last_message_time.short_description = 'Last Message At'

# ---------------- ChatMessage Admin ----------------
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('room_display', 'sender', 'recipient', 'short_content', 'created_at')
    list_filter = ('room', 'sender', 'recipient')
    search_fields = ('content', 'sender__username', 'recipient__username')
    ordering = ('-created_at',)

    def room_display(self, obj):
        return obj.room.__str__()
    room_display.short_description = 'Room'

    def short_content(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    short_content.short_description = 'Message'