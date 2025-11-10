from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.contrib import admin
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from django.db.models import Avg, Count, Q
import logging
from django.db import IntegrityError

# Get logger instance
logger = logging.getLogger(__name__)





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
    active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        """Ensure end_date is timezone aware"""
        if self.end_date and timezone.is_naive(self.end_date):
            self.end_date = timezone.make_aware(self.end_date)
            logger.info(f"Converted naive datetime to aware: {self.end_date}")
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        """Check if this specific ban is currently active (not expired)"""
        now = timezone.now()
        return self.active and now < self.end_date



    @property
    def time_remaining(self):
        """Get remaining time for active bans"""
        if not self.is_active:
            return "Expired"
        remaining = self.end_date - timezone.now()
        if remaining.days > 0:
            return f"{remaining.days} days, {remaining.seconds // 3600} hours"
        elif remaining.seconds > 3600:
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            return f"{hours} hours, {minutes} minutes"
        else:
            minutes = remaining.seconds // 60
            return f"{minutes} minutes"

    @property
    def local_end_date(self):
        """Get end date in local timezone"""
        return timezone.localtime(self.end_date)

    def __str__(self):
        status = "Active" if self.is_active else "Expired"
        admin_name = self.admin.username if self.admin else "System"
        return f"{self.user.username} banned by {admin_name} ({status})"
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
    
    TASK_STATUS_CHOICES = [
    ('open', 'Open for Applications'),
    ('in_progress', 'In Progress'),
    ('waiting_approval', 'Waiting for Owner Approval'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
    ('incomplete', 'Incomplete'),
    ('under_review', 'Under Admin Review'),
]

    # ALL REQUIRED FIELDS - Add the missing ones
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

    # TASK FIELDS
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='assigned_tasks')
    task_status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='open')
    assigned_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    cancelled_by_user = models.BooleanField(default=False)


    worker_started_at = models.DateTimeField(null=True, blank=True)
    worker_completed_at = models.DateTimeField(null=True, blank=True)
    worker_cancelled_at = models.DateTimeField(null=True, blank=True)
    worker_incomplete_at = models.DateTimeField(null=True, blank=True)

    disputed_by_worker = models.BooleanField(default=False)
    disputed_by_owner = models.BooleanField(default=False)
    dispute_reason = models.TextField(blank=True, null=True)
    resolved_by_support = models.BooleanField(default=False)
    support_resolution = models.TextField(blank=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    views_count = models.PositiveIntegerField(default=0)
    last_viewed = models.DateTimeField(null=True, blank=True)
    
    def increment_views(self):
        self.views_count += 1
        self.last_viewed = timezone.now()
        self.save(update_fields=['views_count', 'last_viewed'])

    def __str__(self):
        return f"{self.user.username} - {self.title} - {self.category.name if self.category else 'No Category'}"


    def mark_as_completed(self, by_user=None):
        old_status = self.task_status
        self.task_status = 'completed'
        self.completed_at = timezone.now()
        
        # If this was assigned to someone, create review opportunities
        if self.assigned_to and old_status != 'completed':
            from .models import Review  # Import here to avoid circular imports
            Review.create_mutual_review_opportunity(self)
        
        self.save()

    def save(self, *args, **kwargs):
    # Check if this is an existing post being updated
        if self.pk:
            try:
                old_post = Post.objects.get(pk=self.pk)
                # Auto-create review opportunities when status changes to completed
                if old_post.task_status != 'completed' and self.task_status == 'completed':
                    if self.assigned_to:
                        from .models import Review  
                        Review.create_mutual_review_opportunity(self)
            except Post.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
    @property
    def is_under_review(self):
        return self.task_status == 'under_review' or self.disputes.filter(status__in=['pending', 'under_review']).exists()

    @property
    def has_resolved_dispute(self):
        """Check if this post has a resolved dispute"""
        return self.disputes.filter(dispute_resolved=True).exists()
    
    @property
    def has_active_dispute(self):
        """Check if this post has an active (non-resolved) dispute"""
        return self.disputes.filter(dispute_resolved=False).exists()




class Review(models.Model):
    RATING_CHOICES = [
        (1, '⭐ - Poor'),
        (2, '⭐⭐ - Fair'),
        (3, '⭐⭐⭐ - Good'),
        (4, '⭐⭐⭐⭐ - Very Good'),
        (5, '⭐⭐⭐⭐⭐ - Excellent'),
    ]
    
    REVIEW_TYPE_CHOICES = [
        ('worker_to_owner', 'Worker to Task Owner'),
        ('owner_to_worker', 'Owner to Worker'),
    ]
    
    # Core relationships
    post = models.ForeignKey(
        'Post',  # Using string reference to avoid circular imports
        on_delete=models.CASCADE, 
        related_name='reviews',
        verbose_name='Task Post'
    )
    
    # Who is giving the review
    reviewer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reviews_given',
        verbose_name='Reviewer'
    )
    
    # Who is receiving the review
    reviewed_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_received',
        verbose_name='Reviewed User'
    )
    
    # Review type - who is rating whom
    review_type = models.CharField(
        max_length=20,
        choices=REVIEW_TYPE_CHOICES,
        verbose_name='Review Type'
    )
    
    # Review content
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Star Rating'
    )
    
    comment = models.TextField(
        blank=True, 
        null=True,
        verbose_name='Review Comment',
        help_text='Share your experience working with this person (optional)'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(
        default=True,
        help_text='Mark if this review is verified (not spam)'
    )
    
    class Meta:
        verbose_name = 'User Review'
        verbose_name_plural = 'User Reviews'
        unique_together = ['post', 'reviewer', 'review_type']  # One review per type per user per post
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', 'reviewer']),
            models.Index(fields=['reviewed_user', 'created_at']),
            models.Index(fields=['rating', 'is_verified']),
            models.Index(fields=['review_type']),
        ]
    
    def __str__(self):
        return f"{self.get_review_type_display()} - {self.rating} stars by {self.reviewer.username}"
    
    def save(self, *args, **kwargs):
        # Auto-set the reviewed_user based on review type
        if not self.reviewed_user and self.post:
            if self.review_type == 'worker_to_owner':
                self.reviewed_user = self.post.user  # Task owner
            elif self.review_type == 'owner_to_worker':
                self.reviewed_user = self.post.assigned_to  # Worker
        
        # Call the parent save method
        super().save(*args, **kwargs)
    
    def get_rating_display_with_stars(self):
        """Return rating with star symbols"""
        stars = '⭐' * self.rating
        empty_stars = '☆' * (5 - self.rating)
        return f"{stars}{empty_stars} ({self.rating}/5)"
    
    def get_absolute_url(self):
        return reverse('admin_review_list')
    
    @property
    def is_worker_review(self):
        return self.review_type == 'worker_to_owner'
    
    @property
    def is_owner_review(self):
        return self.review_type == 'owner_to_worker'
    
    @classmethod
    def get_user_rating_stats(cls, user):
        """Get rating statistics for a user"""
        reviews_received = cls.objects.filter(reviewed_user=user, is_verified=True)
        
        stats = reviews_received.aggregate(
            total_reviews=Count('id'),
            avg_rating=Avg('rating'),
            five_star=Count('id', filter=Q(rating=5)),
            four_star=Count('id', filter=Q(rating=4)),
            three_star=Count('id', filter=Q(rating=3)),
            two_star=Count('id', filter=Q(rating=2)),
            one_star=Count('id', filter=Q(rating=1)),
        )
        
        return stats
    
    @classmethod
    def create_mutual_review_opportunity(cls, post):
        """
        Create review records when a task is completed, allowing both parties to review each other
        """
        if post.task_status != 'completed' or not post.assigned_to:
            return None
        
        reviews_created = []
        
        try:
            # Create review opportunity for worker to rate owner
            worker_review, created1 = cls.objects.get_or_create(
                post=post,
                reviewer=post.assigned_to,
                review_type='worker_to_owner',
                defaults={
                    'reviewed_user': post.user,
                    'rating': 0,  # 0 means not rated yet
                    'comment': '',
                }
            )
            if created1:
                reviews_created.append(worker_review)
            
            # Create review opportunity for owner to rate worker
            owner_review, created2 = cls.objects.get_or_create(
                post=post,
                reviewer=post.user,
                review_type='owner_to_worker',
                defaults={
                    'reviewed_user': post.assigned_to,
                    'rating': 0,  # 0 means not rated yet
                    'comment': '',
                }
            )
            if created2:
                reviews_created.append(owner_review)
                
            return {
                'worker_review': worker_review,
                'owner_review': owner_review,
                'reviews_created': reviews_created
            }
            
        except IntegrityError as e:
            logger.error(f"Integrity error creating review opportunities: {e}")
            return None
    @classmethod
    def get_pending_reviews_for_user(cls, user):
        """Get reviews that a user needs to complete"""
        return cls.objects.filter(
            reviewer=user,
            rating=0,  # Not rated yet
            post__task_status='completed'
        )
    
    @classmethod
    def get_completed_reviews_for_post(cls, post):
        """Get completed reviews for a post"""
        return cls.objects.filter(
            post=post,
            rating__gt=0  # Rated
        )












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



class TaskApplication(models.Model):
    """Model for users applying to tasks"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_applications')
    message = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['post', 'applicant']
    
    def __str__(self):
        return f"{self.applicant.username} applied for {self.post.title}"

# Update the Post model to add task status fields
# Add these fields to your existing Post model:

TASK_STATUS_CHOICES = [
    ('open', 'Open for Applications'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
    ('incomplete', 'Incomplete'),
]



class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.message[:50]}"
    




















class UserLoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    device_fingerprint = models.CharField(max_length=255, blank=True, null=True)
    browser = models.CharField(max_length=100, blank=True, null=True)
    os = models.CharField(max_length=100, blank=True, null=True)
    device_type = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "User Login Histories"
        ordering = ['-login_time']

    def __str__(self):
        return f"{self.user.username} - {self.login_time}"

class UserRegistrationData(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='registration_data')
    registration_ip = models.GenericIPAddressField()
    registration_user_agent = models.TextField()
    registration_device_fingerprint = models.CharField(max_length=255)
    registration_browser = models.CharField(max_length=100)
    registration_os = models.CharField(max_length=100)
    registration_device_type = models.CharField(max_length=50)
    registration_country = models.CharField(max_length=100, blank=True, null=True)
    registration_city = models.CharField(max_length=100, blank=True, null=True)
    registration_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Registration data for {self.user.username}"
    



class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"Password reset for {self.user.username}"
    


class TaskDispute(models.Model):
    DISPUTE_TYPES = [
        ('worker_completed_owner_incomplete', 'Worker marked completed, Owner marked incomplete'),
        ('worker_disputed_incomplete', 'Worker disputed incomplete status'),
        ('owner_disputed_completion', 'Owner disputed worker completion'),
        ('direct_message', 'Direct message to admin'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    DECISION_CHOICES = [
        ('completed', 'Mark as Completed'),
        ('cancelled', 'Cancel Task'),
        ('refunded', 'Full Refund'),
        ('split', 'Split Payment'),
    ]
    
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='disputes')
    dispute_type = models.CharField(max_length=50, choices=DISPUTE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # NEW FIELD: Dispute resolved flag
    dispute_resolved = models.BooleanField(default=False, help_text="Whether the dispute has been resolved by admin")
    
    # Who initiated the dispute
    initiated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_disputes')
    
    # The other party involved
    other_party = models.ForeignKey(User, on_delete=models.CASCADE, related_name='involved_disputes', null=True, blank=True)
    
    # Dispute details
    reason = models.TextField(blank=True, null=True)
    worker_evidence = models.TextField(blank=True, null=True, help_text="Worker's evidence for completion")
    owner_evidence = models.TextField(blank=True, null=True, help_text="Owner's evidence for incompletion")
    
    # Admin resolution
    admin_notes = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_disputes')
    resolution = models.TextField(blank=True, null=True)
    admin_decision = models.CharField(max_length=20, choices=DECISION_CHOICES, blank=True, null=True)
    
    # Split payment details (if decision is 'split')
    worker_percentage = models.IntegerField(default=50, help_text="Percentage for worker (0-100)")
    owner_percentage = models.IntegerField(default=50, help_text="Percentage for owner (0-100)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Task Dispute'
        verbose_name_plural = 'Task Disputes'
    
    def __str__(self):
        return f"Dispute #{self.id} - {self.post.title} - {self.get_dispute_type_display()}"
    
    def save(self, *args, **kwargs):
        # Ensure percentages sum to 100 for split decisions
        if self.admin_decision == 'split':
            if self.worker_percentage + self.owner_percentage != 100:
                self.owner_percentage = 100 - self.worker_percentage
        
        # Automatically set dispute_resolved when status is resolved or dismissed
        if self.status in ['resolved', 'dismissed']:
            self.dispute_resolved = True
        else:
            self.dispute_resolved = False
            
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        return self.status in ['pending', 'under_review']
    
    @property
    def is_resolved(self):
        return self.status in ['resolved', 'dismissed']
    
    # Add this new property for dispute resolution status
    @property
    def can_be_disputed_again(self):
        """Check if this dispute can be disputed again"""
        return not self.dispute_resolved
    
    def mark_under_review(self):
        """Mark dispute as under review"""
        self.status = 'under_review'
        self.dispute_resolved = False
        self.save()
    
    def resolve_dispute(self, admin_user, resolution, admin_notes=''):
        """Legacy method for backward compatibility"""
        self.status = 'resolved'
        self.dispute_resolved = True
        self.resolved_by = admin_user
        self.resolution = resolution
        self.admin_notes = admin_notes
        self.resolved_at = timezone.now()
        self.save()
        
        # Update the post status based on resolution text
        if 'complete' in resolution.lower() or 'approve' in resolution.lower():
            self.post.task_status = 'completed'
            self.post.completed_at = timezone.now()
        elif 'incomplete' in resolution.lower() or 'reject' in resolution.lower():
            self.post.task_status = 'incomplete'
        self.post.save()
        return True
    
    def resolve_with_decision(self, decision, admin_user, resolution='', admin_notes='', worker_percentage=50):
        """Resolve dispute with specific decision"""
        self.status = 'resolved'
        self.dispute_resolved = True
        self.resolved_by = admin_user
        self.admin_decision = decision
        self.resolution = resolution
        self.admin_notes = admin_notes
        self.resolved_at = timezone.now()
        
        if decision == 'split':
            self.worker_percentage = worker_percentage
            self.owner_percentage = 100 - worker_percentage
        
        self.save()
        
        # Update post status based on decision
        if decision == 'completed':
            self.post.task_status = 'completed'
            self.post.completed_at = timezone.now()
        elif decision in ['cancelled', 'refunded']:
            self.post.task_status = 'cancelled'
        elif decision == 'split':
            self.post.task_status = 'completed'
        
        self.post.save()
        return True
    
    def reopen_dispute(self):
        """Reopen a resolved dispute"""
        if self.status in ['resolved', 'dismissed']:
            self.status = 'under_review'
            self.dispute_resolved = False
            self.resolved_by = None
            self.resolution = ''
            self.admin_notes = ''
            self.resolved_at = None
            self.admin_decision = None
            self.save()
            
            # Reset post status to under review
            self.post.task_status = 'under_review'
            self.post.save()
            return True
        return False
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('dispute_detail', kwargs={'dispute_id': self.id})


class DisputeMessage(models.Model):
    dispute = models.ForeignKey(TaskDispute, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    image = models.ImageField(upload_to='dispute_messages/%Y/%m/%d/', null=True, blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Dispute Message'
        verbose_name_plural = 'Dispute Messages'
    
    def __str__(self):
        return f"Message from {self.sender.username} in Dispute #{self.dispute.id}"
    
    @property
    def has_image(self):
        return bool(self.image)
    
    def get_image_url(self):
        if self.image:
            return self.image.url
        return None
    
    def to_dict(self):
        """Convert message to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'sender': {
                'id': self.sender.id,
                'username': self.sender.username,
                'is_staff': self.sender.is_staff,
            },
            'message': self.message,
            'image_url': self.get_image_url(),
            'created_at': self.created_at.isoformat(),
            'formatted_time': self.created_at.strftime('%b %d, %Y %H:%M'),
            'has_image': self.has_image,
        }


class DisputeEvidence(models.Model):
    EVIDENCE_TYPES = [
        ('image', 'Image'),
        ('document', 'Document'),
        ('other', 'Other'),
    ]
    
    dispute = models.ForeignKey(TaskDispute, on_delete=models.CASCADE, related_name='evidence_files')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_evidence')
    file = models.FileField(upload_to='dispute_evidence/%Y/%m/%d/', max_length=500)
    file_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES, default='image')
    description = models.TextField(blank=True, null=True)
    is_initial = models.BooleanField(default=False, help_text="Whether this is initial evidence submitted with dispute")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dispute Evidence'
        verbose_name_plural = 'Dispute Evidence'
    
    def __str__(self):
        return f"Evidence #{self.id} for Dispute #{self.dispute.id}"
    
    def save(self, *args, **kwargs):
        # Automatically determine file type based on extension
        if self.file:
            extension = self.file.name.split('.')[-1].lower()
            if extension in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
                self.file_type = 'image'
            elif extension in ['pdf', 'doc', 'docx', 'txt', 'rtf']:
                self.file_type = 'document'
            else:
                self.file_type = 'other'
        super().save(*args, **kwargs)
    
    @property
    def filename(self):
        if self.file:
            return self.file.name.split('/')[-1]
        return "No file"
    
    @property
    def is_image(self):
        return self.file_type == 'image'
    
    @property
    def is_document(self):
        return self.file_type == 'document'
    
    def get_file_url(self):
        if self.file:
            return self.file.url
        return None
    
    def get_file_icon(self):
        if self.is_image:
            return 'fa-image'
        elif self.is_document:
            return 'fa-file-alt'
        else:
            return 'fa-file'
    
    def to_dict(self):
        """Convert evidence to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'submitted_by': {
                'id': self.submitted_by.id,
                'username': self.submitted_by.username,
            },
            'file_url': self.get_file_url(),
            'file_type': self.file_type,
            'filename': self.filename,
            'description': self.description,
            'is_initial': self.is_initial,
            'created_at': self.created_at.isoformat(),
            'formatted_time': self.created_at.strftime('%b %d, %Y %H:%M'),
            'is_image': self.is_image,
            'icon_class': self.get_file_icon(),
        }