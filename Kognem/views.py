# core/views.py
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils.timezone import now
from django.conf import settings
import os, json, re
from django.contrib.auth.models import User
from .models import Profile,Post,BanLog, Logo
from .forms import CustomUserCreationForm, EmailOrUsernameAuthenticationForm
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from .models import Post, ChatMessage, Room
from .forms import PostForm 
from django.contrib.sessions.models import Session # <-- НОВЫЙ ИМПОРТ ДЛЯ РАЗЛОГИНИВАНИЯ
from django.utils.timezone import now
from django.conf import settings
from django.utils import timezone # <--- Отсюда вы берете timezone.utc
from datetime import timedelta,datetime
from django.shortcuts import get_object_or_404
# from .models import ChatNotification
from channels.db import database_sync_to_async
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import Post, Logo, Profile, Category, State, Province
import requests
from django.shortcuts import render, redirect
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden 
from .models import Post , TaskApplication ,  Notification
from .utils.device_fingerprint import generate_device_fingerprint, parse_user_agent
from .utils.geolocation import get_geolocation, get_client_ip
from .models import UserLoginHistory, UserRegistrationData,TaskDispute
import logging
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Count, Q
from .models import Review, Post , DisputeMessage
from django.core.paginator import Paginator
from django.db import IntegrityError


logger = logging.getLogger(__name__)


#------------------------------ DECORATORS -------------------------------------------------------------------

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role in ['admin', 'superadmin']:
            return view_func(request, *args, **kwargs)
        messages.error(request, "Դուք չունեք թույլտվություն մուտք գործելու այս էջ:")
        return redirect('home')
    return wrapper


def superadmin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'superadmin':
            return view_func(request, *args, **kwargs)
        messages.error(request, "Դուք չունեք թույլտվություն մուտք գործելու այս էջ:")
        return redirect('home')
    return wrapper

def moderator_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_superuser or request.user.profile.role in ['admin', 'moderator']):
            return view_func(request, *args, **kwargs)
        messages.error(request, "Դուք չունեք թույլտվություն մուտք գործելու այս էջ:")
        return redirect('home')
    return wrapper



@property
def is_banned(self):
    now = timezone.now()
    return self.user.bans.filter(active=True, end_date__gt=now).exists()



#-------------------------------CHAT LOGIC , MESSAGES-------------------------------------------------------------


@login_required
def create_room(request, username):
    other_user = get_object_or_404(User, username=username)
    room_name = f"room_{min(request.user.id, other_user.id)}_{max(request.user.id, other_user.id)}"
    room, _ = Room.objects.get_or_create(name=room_name)
    room.users.add(request.user, other_user)
    return redirect('chat_room', user_id=other_user.id)


@login_required
def chat_room(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    room_name = f"room_{min(request.user.id, other_user.id)}_{max(request.user.id, other_user.id)}"
    room, _ = Room.objects.get_or_create(name=room_name)
    room.users.add(request.user, other_user)

    messages_qs = ChatMessage.objects.filter(room=room).order_by('created_at')
    messages_data = [m.to_dict() for m in messages_qs]

    return render(request, 'chat/chat.html', {
        'room_name': room.name,
        'other': other_user,
        'messages': messages_data
    })


@login_required
def get_messages(request, username):
    other_user = get_object_or_404(User, username=username)
    room_name = f"room_{min(request.user.id, other_user.id)}_{max(request.user.id, other_user.id)}"
    room = get_object_or_404(Room, name=room_name)
    messages_qs = ChatMessage.objects.filter(room=room).order_by('created_at')

    messages_data = [{
        'sender': msg.sender.username,
        'content': msg.content,
        'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
    } for msg in messages_qs]

    return JsonResponse({'messages': messages_data})

@login_required
def get_messages_by_id(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    room_name = f"room_{min(request.user.id, other_user.id)}_{max(request.user.id, other_user.id)}"
    room = get_object_or_404(Room, name=room_name)
    messages_qs = ChatMessage.objects.filter(room=room).order_by('created_at')

    messages_data = [{
        'sender': msg.sender.username,
        'content': msg.content,
        'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
    } for msg in messages_qs]

    return JsonResponse({'messages': messages_data})




@login_required
def send_message(request, user_id):
    """Save a message via POST (used by AJAX/WebSocket fallback)."""
    if request.method == 'POST':
        text = request.POST.get('text')
        if not text:
            return JsonResponse({'error': 'Empty message'}, status=400)

        other_user = get_object_or_404(User, pk=user_id)
        room_name = f"room_{min(request.user.id, other_user.id)}_{max(request.user.id, other_user.id)}"
        room, _ = Room.objects.get_or_create(name=room_name)
        room.users.add(request.user, other_user)

        message = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            recipient=other_user,
            content=text
        )

        return JsonResponse({'message': message.to_dict()})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def messages_list(request):
    user = request.user

    # Get all unique users you have exchanged messages with
    sent_users = ChatMessage.objects.filter(sender=user).values_list('recipient', flat=True)
    received_users = ChatMessage.objects.filter(recipient=user).values_list('sender', flat=True)

    user_ids = set(list(sent_users) + list(received_users))
    users = User.objects.filter(id__in=user_ids)

    return render(request, 'messages_list.html', {'users': users})

# ------------------------------------------TASK,Post CODES ----------------------------------------------------------------
def task_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    return render(request, 'task_detail.html', {'post': post})

@login_required
def view_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # Allow viewing if:
    # 1. User is post owner OR
    # 2. User is assigned worker OR  
    # 3. Post is approved (public) OR
    # 4. User is admin/moderator
    can_view = (
        post.user == request.user or
        post.assigned_to == request.user or
        post.status == 'approved' or
        (hasattr(request.user, 'profile') and 
         request.user.profile.role in ['admin', 'moderator', 'superadmin'])
    )
    
    if not can_view:
        messages.error(request, "You don't have permission to view this post.")
        return redirect('myposts')
    
    return render(request, 'Account/post_detail.html', {'post': post})

@login_required(login_url='login')
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.status = 'pending'  # All new posts start as pending
            post.save()
            messages.success(request, 'Your post has been submitted and is pending approval.')
            return redirect('admin_dashboard')  # Redirect to admin dashboard
    else:
        form = PostForm()
    return render(request, 'create_post.html', {'form': form})


@admin_required 
def post_management(request):
    current_status = request.GET.get('status', 'all')
    base_queryset = Post.objects.select_related('user').all().order_by('-created_at')
    counts = base_queryset.aggregate(
        all_posts_count=Count('id'),
        pending_posts_count=Count('id', filter=Q(status='pending')),
        approved_posts_count=Count('id', filter=Q(status='approved')),
        rejected_posts_count=Count('id', filter=Q(status='rejected')),
    )

    # ----------- FILTER posteri hamar---------------------
    if current_status == 'pending':
        posts = base_queryset.filter(status='pending')
        table_title = "Pending Posts"
    elif current_status == 'approved':
        posts = base_queryset.filter(status='approved')
        table_title = "Approved Posts"
    elif current_status == 'rejected':
        posts = base_queryset.filter(status='rejected')
        table_title = "Rejected Posts"
    else:
        posts = base_queryset
        table_title = "All Posts"
        current_status = 'all'

    context = {
        
        'all_posts_count': counts['all_posts_count'],
        'pending_posts_count': counts['pending_posts_count'],
        'approved_posts_count': counts['approved_posts_count'],
        'rejected_posts_count': counts['rejected_posts_count'],
        
        
        'posts': posts, 
        'current_status': current_status, 
        'table_title': table_title,
    }
    
    return render(request, 'admin/post_management.html', context)

#----------------------------------- ADMINI ARAVELUTYUNNER ---------------------------------------
@csrf_exempt
@admin_required
def approve_post(request, post_id):
    try:
        post = Post.objects.get(pk=post_id)
        post.status = 'approved'
        post.save()
        return JsonResponse({"success": True})
    except Post.DoesNotExist:
        return JsonResponse({"success": False, "error": "Post not found"}, status=404)

@csrf_exempt
@admin_required
def reject_post(request, post_id):
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)
        
    try:
        post = Post.objects.get(pk=post_id)
        
        try:
            data = json.loads(request.body)
            rejection_reason = data.get('reason', '').strip()
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON format"}, status=400)

        if not rejection_reason:
            return JsonResponse({"success": False, "error": "Rejection reason is required"}, status=400)
            
        post.status = 'rejected'
        post.rejection_reason = rejection_reason 
        post.save()
        
        return JsonResponse({"success": True})
        
    except Post.DoesNotExist:
        return JsonResponse({"success": False, "error": "Post not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@admin_required
def approved_posts_view(request):
    posts = Post.objects.filter(status='approved').order_by('-created_at')
    return render(request, 'admin/approved_posts.html', {'posts': posts})


@admin_required
def rejected_posts_view(request):
    posts = Post.objects.filter(status='rejected').order_by('-created_at')
    return render(request, 'admin/rejected_posts.html', {'posts': posts})


@admin_required
def pending_posts_view(request):
    posts = Post.objects.filter(status='pending').order_by('-created_at')

    return render(request, 'admin/pending_posts.html', {'posts': posts})

@admin_required
def review_posts(request):
    return render(request, 'admin/review_posts.html')

@admin_required
def admin_review_list(request):
    """Admin view to see all reviews with filtering options"""
    reviews = Review.objects.select_related('post', 'reviewer', 'reviewed_user').filter(rating__gt=0)
    
    filtered_user = None
    
    # Filter by user if provided
    user_id = request.GET.get('user_id')
    if user_id:
        try:
            filtered_user = User.objects.get(id=user_id)
            reviews = reviews.filter(
                Q(reviewer_id=user_id) | Q(reviewed_user_id=user_id)
            )
        except User.DoesNotExist:
            pass
    
    # Filter by rating if provided
    rating = request.GET.get('rating')
    if rating:
        reviews = reviews.filter(rating=rating)
    
    # Filter by review type if provided
    review_type = request.GET.get('review_type')
    if review_type:
        reviews = reviews.filter(review_type=review_type)
    
    # Filter by specific review ID if provided
    review_id = request.GET.get('review_id')
    if review_id:
        reviews = reviews.filter(id=review_id)
    
    # Calculate stats
    total_reviews = reviews.count()
    average_rating = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    owner_reviews_count = reviews.filter(review_type='owner_to_worker').count()
    worker_reviews_count = reviews.filter(review_type='worker_to_owner').count()
    
    # Add user stats if filtered by user
    if filtered_user:
        filtered_user.avg_rating = filtered_user.reviews_received.filter(rating__gt=0).aggregate(
            avg_rating=Avg('rating')
        )['avg_rating'] or 0
    
    context = {
        'reviews': reviews,
        'total_reviews': total_reviews,
        'average_rating': round(average_rating, 2),
        'owner_reviews_count': owner_reviews_count,
        'worker_reviews_count': worker_reviews_count,
        'filtered_user': filtered_user,
        'filtered_user_id': user_id,
        'filtered_rating': rating,
        'filtered_review_type': review_type,
    }
    return render(request, 'admin/admin_review_list.html', context)



@admin_required
def user_ratings_report(request):
    """Admin report showing user ratings statistics"""
    from django.db.models import Avg, Count, Max, Q
    
    # Get users with their review stats
    users = User.objects.filter(
        reviews_received__rating__gt=0
    ).annotate(
        avg_rating=Avg('reviews_received__rating'),
        review_count=Count('reviews_received'),
        completed_tasks=Count('assigned_tasks', filter=Q(assigned_tasks__task_status='completed')),
        last_review_date=Max('reviews_received__created_at'),
        worker_reviews=Count('reviews_received', filter=Q(reviews_received__review_type='owner_to_worker')),
        owner_reviews=Count('reviews_received', filter=Q(reviews_received__review_type='worker_to_owner')),
        five_star=Count('reviews_received', filter=Q(reviews_received__rating=5)),
        four_star=Count('reviews_received', filter=Q(reviews_received__rating=4)),
        three_star=Count('reviews_received', filter=Q(reviews_received__rating=3)),
        two_star=Count('reviews_received', filter=Q(reviews_received__rating=2)),
        one_star=Count('reviews_received', filter=Q(reviews_received__rating=1)),
    ).distinct()
    
    # Calculate additional metrics
    for user in users:
        if user.review_count > 0:
            user.five_star_percent = (user.five_star / user.review_count) * 100
            user.four_star_percent = (user.four_star / user.review_count) * 100
            user.three_star_percent = (user.three_star / user.review_count) * 100
            user.two_star_percent = (user.two_star / user.review_count) * 100
            user.one_star_percent = (user.one_star / user.review_count) * 100
            user.reliability_score = user.avg_rating
        else:
            user.five_star_percent = user.four_star_percent = user.three_star_percent = 0
            user.two_star_percent = user.one_star_percent = 0
            user.reliability_score = 0
    
    # Platform statistics
    from .models import Review
    total_reviews = Review.objects.filter(rating__gt=0).count()
    platform_stats = {
        'total_rated_users': users.count(),
        'total_reviews': total_reviews,
        'platform_avg_rating': Review.objects.filter(rating__gt=0).aggregate(Avg('rating'))['rating__avg'] or 0,
        'five_star_count': Review.objects.filter(rating=5).count(),
        'five_star_percent': (Review.objects.filter(rating=5).count() / total_reviews * 100) if total_reviews > 0 else 0,
        'four_star_percent': (Review.objects.filter(rating=4).count() / total_reviews * 100) if total_reviews > 0 else 0,
        'three_star_percent': (Review.objects.filter(rating=3).count() / total_reviews * 100) if total_reviews > 0 else 0,
        'two_star_percent': (Review.objects.filter(rating=2).count() / total_reviews * 100) if total_reviews > 0 else 0,
        'one_star_percent': (Review.objects.filter(rating=1).count() / total_reviews * 100) if total_reviews > 0 else 0,
    }
    
    context = {
        'users': users,
        'platform_stats': platform_stats,
        'total_rated_users': users.count(),
        'current_filters': request.GET.dict(),
        'sort_options': [
            ('avg_rating', 'Average Rating'),
            ('review_count', 'Number of Reviews'),
            ('completed_tasks', 'Completed Tasks'),
            ('username', 'Username'),
        ]
    }
    
    return render(request, 'admin/user_ratings_report.html', context)

@login_required
def edit_post(request, post_id):
    """Редактирование поста с гарантированной отправкой на модерацию"""
    post = get_object_or_404(Post, id=post_id)
    
    # Проверяем, что пользователь является владельцем поста
    if post.user != request.user:
        messages.error(request, "Դուք կարող եք խմբագրել միայն ձեր սեփական հայտարարությունները:")
        return redirect('view_post', post_id=post_id)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            try:
                # Сохраняем форму
                form.save()
                
                # ГАРАНТИРОВАННО меняем статус на pending через прямое обновление
                Post.objects.filter(id=post_id).update(
                    status='pending',
                    rejection_reason=''
                )
                
                messages.success(request, '✅ Հայտարարությունը հաջողությամբ խմբագրվել և ուղարկվել է ադմինիստրացիա ստուգման համար:')
                return redirect('myposts')  # Перенаправляем на страницу аккаунта
                
            except Exception as e:
                print(f"Սխալ պահպանման ժամանակ: {e}")
                messages.error(request, f'❌ Սխալ պահպանման ժամանակ: {e}')
        else:
            messages.error(request, '❌ Խնդրում ենք ուղղել ֆորմայի սխալները:')
    else:
        form = PostForm(instance=post)
    
    return render(request, 'edit_post.html', {
        'form': form,
        'post': post
    })

@login_required
def send_for_moderation(request, post_id):
    """Отдельная функция для отправки поста на модерацию"""
    try:
        post = Post.objects.get(id=post_id, user=request.user)
        
        # Прямое обновление статуса
        Post.objects.filter(id=post_id).update(
            status='pending',
            rejection_reason=''
        )
        
        messages.success(request, '✅ Пост отправлен на проверку администраторам!')
        return redirect('myposts')
        
    except Post.DoesNotExist:
        messages.error(request, '❌ Пост не найден')
        return redirect('myposts')

@login_required
def delete_post(request, post_id):
    """Удаление поста"""
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        
        # Проверяем, что пользователь является владельцем поста
        if post.user != request.user:
            messages.error(request, "Вы можете удалять только свои посты.")
            return redirect('view_post', post_id=post_id)
        
        post_title = post.title
        post.delete()
        
        messages.success(request, f'Пост "{post_title}" успешно удален.')
        return redirect('myposts')
    
    return redirect('view_post', post_id=post_id)

# ---------------- Admin Dashboard ----------------
@admin_required
def admin_dashboard(request):
    # Get filter parameters from request
    user_filter = request.GET.get('user_filter', 'all')
    date_range = request.GET.get('date_range', 'all')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort_by', '-date_joined')
    
    # Base queryset for users - PREFETCH BAN INFORMATION
    users_queryset = User.objects.all().prefetch_related(
        'bans'  # This matches the related_name in BanLog model
    )
    
    # Apply user status filter
    if user_filter == 'active':
        users_queryset = users_queryset.filter(is_active=True)
    elif user_filter == 'banned':
        users_queryset = users_queryset.filter(is_active=False)
    elif user_filter == 'rated':
        users_queryset = users_queryset.filter(
            reviews_received__rating__gt=0
        ).distinct()
    elif user_filter == 'unrated':
        users_queryset = users_queryset.exclude(
            reviews_received__rating__gt=0
        ).distinct()
    
    # Apply search filter
    if search_query:
        users_queryset = users_queryset.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Apply date range filter
    if date_range != 'all':
        today = timezone.now().date()
        if date_range == 'today':
            start_date = today
        elif date_range == 'week':
            start_date = today - timedelta(days=7)
        elif date_range == 'month':
            start_date = today - timedelta(days=30)
        elif date_range == 'year':
            start_date = today - timedelta(days=365)
        
        users_queryset = users_queryset.filter(date_joined__date__gte=start_date)
    
    # Apply sorting and annotations
    users_queryset = users_queryset.annotate(
        review_count=Count('reviews_received', filter=Q(reviews_received__rating__gt=0)),
        avg_rating=Avg('reviews_received__rating', filter=Q(reviews_received__rating__gt=0))
    ).order_by(sort_by)
    
    # Pagination
    paginator = Paginator(users_queryset, 25)  # Show 25 users per page
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    # Add active_ban property to each user for template access
    for user in users_page:
        # Get the active ban (not expired and active=True)
        active_ban = user.bans.filter(active=True, end_date__gt=timezone.now()).first()
        user.active_ban = active_ban
    
    # Existing user counts (unfiltered for stats)
    all_users_count = User.objects.count()
    active_users_count = User.objects.filter(is_active=True).count()
    banned_users_count = User.objects.filter(is_active=False).count()
    
    # Review statistics
    total_reviews_count = Review.objects.filter(rating__gt=0).count()
    average_rating = Review.objects.filter(rating__gt=0).aggregate(
        avg_rating=Avg('rating')
    )['avg_rating'] or 0
    
    # Count users who have received reviews (with rating > 0)
    rated_users_count = User.objects.filter(
        reviews_received__rating__gt=0
    ).distinct().count()
    
    # Recent reviews for the dashboard (only completed reviews with ratings)
    recent_reviews = Review.objects.filter(rating__gt=0).select_related(
        'reviewer', 'reviewed_user', 'post'
    ).order_by('-created_at')[:5]
    
    # Additional stats for the dashboard
    completed_posts_with_reviews = Post.objects.filter(
        task_status='completed',
        reviews__rating__gt=0
    ).distinct().count()
    
    pending_reviews_count = Review.objects.filter(rating=0).count()
    
    # Filter stats based on current filters
    filtered_users_count = users_queryset.count()
    
    context = {
        # User counts
        'all_users_count': all_users_count,
        'active_users_count': active_users_count,
        'banned_users_count': banned_users_count,
        'rated_users_count': rated_users_count,
        'filtered_users_count': filtered_users_count,
        
        # Review stats
        'total_reviews_count': total_reviews_count,
        'average_rating': round(average_rating, 2),
        'completed_posts_with_reviews': completed_posts_with_reviews,
        'pending_reviews_count': pending_reviews_count,
        
        # Data
        'users': users_page,
        'recent_reviews': recent_reviews,
        
        # Filter parameters
        'current_user_filter': user_filter,
        'current_date_range': date_range,
        'current_search': search_query,
        'current_sort': sort_by,
        
        # Options for filters
        'user_filters': [
            ('all', 'All Users'),
            ('active', 'Active Users'),
            ('banned', 'Banned Users'),
            ('rated', 'Users with Reviews'),
            ('unrated', 'Users without Reviews'),
        ],
        'date_ranges': [
            ('all', 'All Time'),
            ('today', 'Today'),
            ('week', 'Last 7 Days'),
            ('month', 'Last 30 Days'),
            ('year', 'Last Year'),
        ],
        'sort_options': [
            ('-date_joined', 'Newest First'),
            ('date_joined', 'Oldest First'),
            ('-review_count', 'Most Reviews'),
            ('review_count', 'Fewest Reviews'),
            ('-avg_rating', 'Highest Rated'),
            ('avg_rating', 'Lowest Rated'),
            ('username', 'Username A-Z'),
            ('-username', 'Username Z-A'),
        ],
        
        'page_title': 'Admin Dashboard',
    }
    
    return render(request, 'admin/dashboard.html', context)

@admin_required
def user_detail(request, user_id):
    try:
        target_user = User.objects.select_related('profile').get(pk=user_id)
        posts = Post.objects.filter(user=target_user).order_by('-created_at')  
        current_user_role = request.user.profile.role

        if request.user.profile.role == 'admin' and target_user.profile.role in ['admin', 'superadmin', 'support']:
            messages.error(request, "Դուք չեք կարող մուտք գործել այս օգտվողի էջը")
            return redirect('admin_dashboard')

        return render(request, 'admin/user_detail.html', {
            'target_user': target_user,
            'posts': posts,
            'current_user': request.user
        })
    except User.DoesNotExist:
        messages.error(request, "Օգտվողը չի գտնվել")
        return redirect('admin_dashboard')



@admin_required
def all_users(request):
    """View for all users"""
    users = User.objects.select_related("profile").prefetch_related('bans').all()
    
    for user in users:
        try:
            user.active_ban = user.bans.filter(active=True).order_by('-end_date').first()
        except AttributeError:
            user.active_ban = None
    
    all_users_count = User.objects.count()
    active_users_count = User.objects.filter(is_active=True).count()
    banned_users_count = User.objects.filter(is_active=False).count()
    
    return render(request, "admin/dashboard.html", {
        "users": users,
        "all_users_count": all_users_count,
        "active_users_count": active_users_count,
        "banned_users_count": banned_users_count,
        "current_filter": "all",
        "page_title": "All Users"
    })

@admin_required
def active_users(request):
    """View for active users only"""
    now = timezone.now()
    users = User.objects.filter(is_active=True).select_related("profile").prefetch_related('bans').all()
    
    for user in users:
        try:
            # Only get ACTIVE bans (not expired)
            user.active_ban = user.bans.filter(active=True, end_date__gt=now).order_by('-end_date').first()
        except AttributeError:
            user.active_ban = None
    
    all_users_count = User.objects.count()
    active_users_count = User.objects.filter(is_active=True).count()
    banned_users_count = User.objects.filter(is_active=False).count()
    
    return render(request, "admin/dashboard.html", {
        "users": users,
        "all_users_count": all_users_count,
        "active_users_count": active_users_count,
        "banned_users_count": banned_users_count,
        "current_filter": "active",
        "page_title": "Active Users"
    })

@admin_required
def banned_users(request):
    """View for banned users only"""
    now = timezone.now()
    users = User.objects.filter(is_active=False).select_related("profile").prefetch_related('bans').all()
    
    for user in users:
        try:
            # Only get ACTIVE bans (not expired)
            user.active_ban = user.bans.filter(active=True, end_date__gt=now).order_by('-end_date').first()
        except AttributeError:
            user.active_ban = None
    
    all_users_count = User.objects.count()
    active_users_count = User.objects.filter(is_active=True).count()
    banned_users_count = User.objects.filter(is_active=False).count()
    
    return render(request, "admin/dashboard.html", {
        "users": users,
        "all_users_count": all_users_count,
        "active_users_count": active_users_count,
        "banned_users_count": banned_users_count,
        "current_filter": "banned",
        "page_title": "Banned Users"
    })



@csrf_exempt
@admin_required
def ban_user(request, user_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)

    try:
        user = User.objects.get(pk=user_id)
        if user.profile.role == 'superadmin':
            return JsonResponse({"success": False, "error": "Cannot ban a superadmin"}, status=403)

        data = json.loads(request.body)
        reason = data.get("reason")
        end_date_str = data.get("end_date")
        
        if not reason or not end_date_str:
            return JsonResponse({"success": False, "error": "Reason and end date required"}, status=400)

        # DEBUG: Log the received date string
        logger.info(f"Received end_date string: {end_date_str}")

        try:
            # Parse the date string - handle different formats
            if 'Z' in end_date_str:
                # UTC format: 2024-01-15T13:02:00Z
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            elif '+' in end_date_str:
                # Already has timezone: 2024-01-15T13:02:00+04:00
                end_date = datetime.fromisoformat(end_date_str)
            else:
                # Naive datetime: 2024-01-15T13:02
                end_date = datetime.fromisoformat(end_date_str)
                # Assume it's in local time and make it aware
                end_date = timezone.make_aware(end_date)
                
            # Convert to UTC for storage using the correct method
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
            # Now convert to UTC timezone
            end_date_utc = end_date.astimezone(timezone.get_current_timezone())  # This converts to server timezone
            # If you want pure UTC, use:
            # end_date_utc = timezone.localtime(end_date, timezone=timezone.utc) if you need UTC
            
        except ValueError as e:
            logger.error(f"Date parsing error: {e}")
            return JsonResponse({"success": False, "error": f"Invalid date format: {str(e)}"}, status=400)

        # DEBUG: Log the parsed dates
        logger.info(f"Parsed local time: {end_date}")
        logger.info(f"Converted time: {end_date_utc}")
        logger.info(f"Current server time: {timezone.now()}")

        # Check if end date is in the future
        if end_date_utc <= timezone.now():
            return JsonResponse({"success": False, "error": "End date must be in the future"}, status=400)

        # Create ban record with the converted time
        ban = BanLog.objects.create(
            user=user,
            admin=request.user,
            reason=reason,
            end_date=end_date_utc,
            active=True
        )

        # Log out user if they're logged in
        from django.contrib.sessions.models import Session
        for session in Session.objects.all():
            session_data = session.get_decoded()
            if str(session_data.get('_auth_user_id')) == str(user.id):
                session.delete()

        # Deactivate user account
        user.is_active = False
        user.save()

        # Get local time for response message
        local_end_time = timezone.localtime(end_date_utc)
        
        logger.info(f"User {user.username} banned by {request.user.username} until {local_end_time}")

        return JsonResponse({
            "success": True, 
            "message": f"User banned until {local_end_time.strftime('%Y-%m-%d %H:%M')}",
            "ban_id": ban.id,
            "local_time": local_end_time.strftime('%Y-%m-%d %H:%M')
        })

    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)
    except Exception as e:
        logger.error(f"Error banning user: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": f"Internal server error: {str(e)}"}, status=500)



@admin_required
def unban_user(request, user_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    try:
        user = User.objects.get(pk=user_id)
        now = timezone.now()

        # Deactivate all active bans
        active_bans = user.bans.filter(active=True)
        ban_count = active_bans.count()
        active_bans.update(active=False)

        # Also update any expired bans that are still marked active
        expired_bans = user.bans.filter(active=True, end_date__lte=now)
        expired_count = expired_bans.count()
        expired_bans.update(active=False)

        # Reactivate user account
        user.is_active = True
        user.save()

        logger.info(f"User {user.username} unbanned by {request.user.username}. {ban_count} active + {expired_count} expired bans deactivated.")

        return JsonResponse({
            "success": True, 
            "message": f"User {user.username} successfully unbanned. {ban_count + expired_count} ban(s) removed."
        })

    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)
    except Exception as e:
        logger.error(f"Error unbanning user: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": f"Internal server error: {str(e)}"}, status=500)
    


@admin_required
def check_ban_status(request, user_id):
    """Debug view to check ban status"""
    try:
        user = User.objects.get(pk=user_id)
        now = timezone.now()
        
        active_bans = user.bans.filter(active=True, end_date__gt=now)
        expired_bans = user.bans.filter(active=True, end_date__lte=now)
        all_bans = user.bans.all()
        
        ban_info = {
            'user': user.username,
            'is_active': user.is_active,
            'current_time_utc': now.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'current_time_local': timezone.localtime(now).strftime('%Y-%m-%d %H:%M:%S Local'),
            'active_bans_count': active_bans.count(),
            'expired_bans_count': expired_bans.count(),
            'total_bans': all_bans.count(),
            'active_bans': []
        }
        
        for ban in active_bans:
            ban_info['active_bans'].append({
                'id': ban.id,
                'reason': ban.reason,
                'end_date_utc': ban.end_date.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'end_date_local': timezone.localtime(ban.end_date).strftime('%Y-%m-%d %H:%M:%S Local'),
                'is_active': ban.is_active,
                'time_remaining': ban.time_remaining
            })
            
        return JsonResponse(ban_info)
        
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
@csrf_exempt
@admin_required
def delete_user(request, user_id):
    try:
        user_to_delete = User.objects.get(pk=user_id)
        if request.user.profile.role == 'admin' and user_to_delete.profile.role in ['admin', 'superadmin', 'support']:
            return JsonResponse({"success": False, "error": "Cannot delete this user"}, status=403)
        user_to_delete.delete()
        return JsonResponse({"success": True})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Internal server error: {str(e)}"}, status=500)

@csrf_exempt
@admin_required
def reset_password(request, user_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST request required"}, status=400)

    try:
        user_to_reset = User.objects.get(pk=user_id)

        target_role = user_to_reset.profile.role
        requester_role = request.user.profile.role

        ROLE_POWER = {"superadmin": 3, "admin": 2, "support": 1, "user": 0}
        if ROLE_POWER.get(requester_role, 0) <= ROLE_POWER.get(target_role, 0) and requester_role != "superadmin":
            return JsonResponse({
                "success": False,
                "error": "You do not have permission to reset this user's password."
            }, status=403)

        data = json.loads(request.body.decode("utf-8"))
        new_password = data.get("password")

        if not new_password:
            return JsonResponse({"success": False, "error": "New password is required"}, status=400)

        user_to_reset.set_password(new_password)
        user_to_reset.save()

        return JsonResponse({"success": True, "message": "Password reset successfully"})

    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

# ---------------- Role Decorators ----------------

def moderator_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_superuser or request.user.profile.role in ['admin', 'moderator']):
            return view_func(request, *args, **kwargs)
        messages.error(request, "Դուք չունեք թույլտվություն մուտք գործելու այս էջ:")
        return redirect('home')
    return wrapper

# ---------------- Home / Landing Pages ----------------
def start(request):
    logo = Logo.objects.first()

    if request.method == "POST" and "guest" in request.POST:
        if request.user.is_authenticated:
            logout(request)
        return redirect("home")
    return render(request, "start.html", context={
        logo:'logo'
    }
    )

def home(request):
    full_name = None
    logo = Logo.objects.first()

    if request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        full_name = profile.full_name or request.user.username

    category_id = request.GET.get('category')
    state_id = request.GET.get('state')
    province_id = request.GET.get('province')

    approved_posts = Post.objects.filter(status='approved').order_by('-created_at')

    if category_id:
        approved_posts = approved_posts.filter(category_id=category_id)
    if state_id:
        approved_posts = approved_posts.filter(state_id=state_id)
    if province_id:
        approved_posts = approved_posts.filter(province_id=province_id)

    categories = Category.objects.all()
    states = State.objects.all()
    provinces = Province.objects.filter(state_id=state_id) if state_id else []

    return render(request, 'home.html', {
        'nav_item':'home',
        'full_name': full_name,
        'posts': approved_posts,
        'logo': logo,
        'categories': categories,
        'states': states,
        'provinces': provinces
    })


def ashxatanq(request):
    approved_posts = Post.objects.filter(status='approved').order_by('-created_at')

    return render(request, 'ashxatanq.html', {
        'posts': approved_posts,
        'nav_item':'ashxatanq',

    })

















# Add this to views.py for debugging
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

def debug_tracking(request):
    """Debug view to test if tracking works"""
    try:
        from .utils.device_fingerprint import generate_device_fingerprint, parse_user_agent
        from .utils.geolocation import get_geolocation, get_client_ip
        from .models import UserLoginHistory, UserRegistrationData
        
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        device_fingerprint = generate_device_fingerprint(request)
        device_info = parse_user_agent(user_agent)
        geolocation = get_geolocation(ip_address)
        
        # Test creating a record
        if request.user.is_authenticated:
            login_record = UserLoginHistory.objects.create(
                user=request.user,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                browser=device_info['browser'],
                os=device_info['os'],
                device_type=device_info['device_type'],
                country=geolocation['country'],
                city=geolocation['city']
            )
            record_id = login_record.id
        else:
            record_id = "User not authenticated"
        
        data = {
            'ip_address': ip_address,
            'user_agent': user_agent,
            'device_fingerprint': device_fingerprint,
            'device_info': device_info,
            'geolocation': geolocation,
            'record_created': record_id,
            'success': True
        }
        
        logger.info(f"Debug tracking successful: {data}")
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"Debug tracking failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)})



# ---------------- Registration / Login / Logout ----------------
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)

            original_username = user.username
            counter = 1
            while User.objects.filter(username=user.username).exists():
                user.username = f"{original_username}{counter}"
                counter += 1
            user.save()

            profile = Profile.objects.create(
                user=user,
                full_name=form.cleaned_data.get('full_name'),
                phone=form.cleaned_data.get('phone'),
                verification_id=form.cleaned_data.get('verification_id'),
                role='user'  
            )

            # === ADD REGISTRATION TRACKING ===
            try:
                from .utils.device_fingerprint import generate_device_fingerprint, parse_user_agent
                from .utils.geolocation import get_geolocation, get_client_ip
                from .models import UserRegistrationData, UserLoginHistory
                
                ip_address = get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                device_fingerprint = generate_device_fingerprint(request)
                device_info = parse_user_agent(user_agent)
                geolocation = get_geolocation(ip_address)
                
                logger.info(f"Tracking registration for {user.username}")
                
                # Save registration data
                UserRegistrationData.objects.create(
                    user=user,
                    registration_ip=ip_address,
                    registration_user_agent=user_agent,
                    registration_device_fingerprint=device_fingerprint,
                    registration_browser=device_info.get('browser', 'Unknown'),
                    registration_os=device_info.get('os', 'Unknown'),
                    registration_device_type=device_info.get('device_type', 'Unknown'),
                    registration_country=geolocation.get('country', 'Unknown'),
                    registration_city=geolocation.get('city', 'Unknown')
                )
                
                logger.info("Registration data saved successfully")
                
            except ImportError as e:
                logger.warning(f"Tracking modules not available: {e}")
            except Exception as e:
                logger.error(f"Error tracking registration: {e}")
            # === END REGISTRATION TRACKING ===

            authenticated_user = authenticate(username=user.username, password=form.cleaned_data.get('password1'))
            if authenticated_user:
                login(request, authenticated_user)
                
                # Also track the initial login after registration
                try:
                    from .models import UserLoginHistory
                    if 'ip_address' in locals() and ip_address:
                        UserLoginHistory.objects.create(
                            user=user,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            device_fingerprint=device_fingerprint,
                            browser=device_info.get('browser', 'Unknown'),
                            os=device_info.get('os', 'Unknown'),
                            device_type=device_info.get('device_type', 'Unknown'),
                            country=geolocation.get('country', 'Unknown'),
                            city=geolocation.get('city', 'Unknown')
                        )
                        logger.info("Initial login after registration tracked")
                    else:
                        logger.warning("Could not track initial login - missing tracking data")
                except Exception as e:
                    logger.error(f"Error tracking initial login: {e}")
                    
            else:
                messages.error(request, "Սխալ ստեղծման ժամանակ: Խնդրում ենք փորձել կրկին.")
                return redirect('register')

            # Your existing JSON code
            json_path = os.path.join(settings.BASE_DIR, 'user_data.json')
            user_data = {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone": profile.phone,
                "verification_id": profile.verification_id,
                "date_joined": now().strftime("%Y-%m-%d %H:%M")
            }
            data = []
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    try: 
                        data = json.load(f)
                    except json.JSONDecodeError: 
                        data = []

            found = False
            for entry in data:
                if entry.get("username") == user.username:
                    entry.update(user_data)
                    found = True
                    break
            if not found:
                data.append(user_data)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            messages.success(request, "Հաջող գրանցում!")
            return redirect('home')
        else:
            messages.error(request, "Խնդրում ենք ուղղել ցուցադրված սխալները:")
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})



def login_view(request):
    """
    Custom login view that prevents banned users from logging in.
    Supports login via username or email with Remember Me functionality.
    """
    logger.info("=== LOGIN VIEW CALLED ===")
    
    if request.user.is_authenticated:
        logger.info("User already authenticated, redirecting to home")
        return redirect('home')

    form = EmailOrUsernameAuthenticationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        logger.info("Login form is valid")
        user = form.get_user()
        now = timezone.now()

        # Update expired bans
        user.bans.filter(active=True, end_date__lt=now).update(active=False)

        # Check for active ban
        active_ban = user.bans.filter(active=True, end_date__gt=now).first()
        if active_ban:
            logger.info(f"User {user.username} is banned")
            messages.error(
                request,
                f"Ձեր հաշիվը արգելված է մինչև {active_ban.end_date.strftime('%Y-%m-%d %H:%M')}"
            )
            return redirect('login')

        # === ADD DEVICE FINGERPRINTING FOR LOGIN (BEFORE LOGIN) ===
        ip_address = None
        user_agent = None
        device_fingerprint = None
        device_info = {'browser': 'Unknown', 'os': 'Unknown', 'device_type': 'Unknown'}
        geolocation = {'country': 'Unknown', 'city': 'Unknown'}
        
        try:
            from .utils.device_fingerprint import generate_device_fingerprint, parse_user_agent
            from .utils.geolocation import get_geolocation, get_client_ip
            from .models import UserLoginHistory
            
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            device_fingerprint = generate_device_fingerprint(request)
            device_info = parse_user_agent(user_agent)
            geolocation = get_geolocation(ip_address)
            
            logger.info(f"Tracking login for {user.username}: IP={ip_address}, Device={device_info.get('device_type', 'Unknown')}")
            
        except ImportError as e:
            logger.warning(f"Tracking modules not available: {e}")
        except Exception as e:
            logger.error(f"Error tracking login: {e}", exc_info=True)
        # === END DEVICE FINGERPRINTING ===

        # Log in the user
        login(request, user)
        logger.info(f"User {user.username} logged in successfully")

        # === HANDLE REMEMBER ME FUNCTIONALITY ===
        remember_me = form.cleaned_data.get('remember_me', True)
        if not remember_me:
            # Session will expire when browser closes
            request.session.set_expiry(0)
            logger.info("Remember Me: OFF - Session will expire when browser closes")
        else:
            # Session will persist for 2 weeks (set in settings)
            request.session.set_expiry(1209600)  # 2 weeks in seconds
            logger.info("Remember Me: ON - Session will persist for 2 weeks")
        # === END REMEMBER ME ===

        # === SAVE LOGIN HISTORY (AFTER SUCCESSFUL LOGIN) ===
        try:
            from .models import UserLoginHistory
            
            login_record = UserLoginHistory.objects.create(
                user=user,
                ip_address=ip_address or 'Unknown',
                user_agent=user_agent or 'Unknown',
                device_fingerprint=device_fingerprint or 'Unknown',
                browser=device_info.get('browser', 'Unknown'),
                os=device_info.get('os', 'Unknown'),
                device_type=device_info.get('device_type', 'Unknown'),
                country=geolocation.get('country', 'Unknown'),
                city=geolocation.get('city', 'Unknown'),
                login_successful=True
            )
            
            logger.info(f"Login history saved successfully with ID: {login_record.id}")
            
        except Exception as e:
            logger.error(f"Error saving login history: {e}", exc_info=True)
        # === END LOGIN HISTORY ===

        # Get or create profile
        profile, _ = Profile.objects.get_or_create(user=user)

        messages.success(
            request,
            f"Բարի վերադարձ, {profile.full_name or user.username}!"
        )
        logger.info("=== LOGIN COMPLETED SUCCESSFULLY ===")
        
        # Redirect to next URL if provided
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('home')
        
    else:
        if request.method == "POST":
            logger.info("Login form is invalid")
            # Log form errors for debugging
            if form.errors:
                logger.error(f"Form errors: {form.errors}")
            
            # Track failed login attempt
            try:
                from .utils.device_fingerprint import generate_device_fingerprint, parse_user_agent
                from .utils.geolocation import get_geolocation, get_client_ip
                from .models import UserLoginHistory
                
                ip_address = get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                device_fingerprint = generate_device_fingerprint(request)
                device_info = parse_user_agent(user_agent)
                geolocation = get_geolocation(ip_address)
                
                # Save failed login attempt
                failed_username = request.POST.get('username', 'Unknown')
                UserLoginHistory.objects.create(
                    user=None,  # No user since login failed
                    ip_address=ip_address,
                    user_agent=user_agent,
                    device_fingerprint=device_fingerprint,
                    browser=device_info.get('browser', 'Unknown'),
                    os=device_info.get('os', 'Unknown'),
                    device_type=device_info.get('device_type', 'Unknown'),
                    country=geolocation.get('country', 'Unknown'),
                    city=geolocation.get('city', 'Unknown'),
                    login_successful=False,
                    attempted_username=failed_username
                )
                
                logger.warning(f"Failed login attempt for username: {failed_username} from IP: {ip_address}")
                
            except Exception as e:
                logger.error(f"Error tracking failed login: {e}")
                
        else:
            logger.info("Login view loaded (GET request)")

    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "Դու դուրս եկար համակարգից։")
    return redirect("start")
# ---------------- Account / Profile ----------------
@login_required
def myinfo(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    json_path = os.path.join(settings.BASE_DIR, 'user_data.json')

    if request.method == 'POST' and request.headers.get("x-requested-with") == "XMLHttpRequest":
        field = request.POST.get('field')
        value = request.POST.get('value', '').strip()

        if field == 'username':
            if len(value) < 3 or User.objects.filter(username=value).exclude(pk=request.user.pk).exists():
                return JsonResponse({"success": False, "error": "Օգտագործանունը արդեն զբաղված կամ կարճ է"})
            request.user.username = value

        elif field == 'full_name':
            parts = value.split()
            if len(parts) < 2:
                return JsonResponse({"success": False, "error": "Մուտքագրեք և անունը, և ազգանունը"})
            request.user.first_name = parts[0]
            request.user.last_name = ' '.join(parts[1:])
            profile.full_name = value

        elif field == 'email':
            if '@' not in value or User.objects.filter(email=value).exclude(pk=request.user.pk).exists():
                return JsonResponse({"success": False, "error": "Սխալ կամ օգտագործված էլ. հասցե"})
            request.user.email = value

        elif field == 'phone':
            if not re.match(r'^0\d{8}$', value):
                return JsonResponse({"success": False, "error": "Հեռախոսը պետք է սկսվի 0-ով և ունենա 9 թվանշան"})
            profile.phone = value

        elif field == 'verification_id':
            if not re.match(r'^[A-Z0-9]+$', value):
                return JsonResponse({"success": False, "error": "Մեծատառ և նիշ, օրինակ ALO123"})
            profile.verification_id = value

        # Save user and profile
        request.user.save()
        profile.save()

        # Update JSON file
        data = []
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                try: data = json.load(f)
                except json.JSONDecodeError: data = []

        found = False
        for entry in data:
            if entry.get("username") == request.user.username:
                entry.update({
                    "username": request.user.username,
                    "first_name": request.user.first_name,
                    "last_name": request.user.last_name,
                    "email": request.user.email,
                    "phone": profile.phone,
                    "verification_id": profile.verification_id,
                    "last_updated": now().strftime("%Y-%m-%d %H:%M")
                })
                found = True
                break
        if not found:
            data.append({
                "username": request.user.username,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "email": request.user.email,
                "phone": profile.phone,
                "verification_id": profile.verification_id,
                "last_updated": now().strftime("%Y-%m-%d %H:%M")
            })

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return JsonResponse({"success": True})

    return render(request, 'Account/myinfo.html', {'profile': profile, 'user': request.user})

@login_required
def Account(request):
    return render(request, 'Account/Account.html')


@login_required
def notifications(request):
    posts = Post.objects.filter(user=request.user).order_by('-updated_at')
    notifications_list = []

    for post in posts:
        if hasattr(post, 'status') and post.status in ['approved', 'rejected']:
            if post.status == 'approved':
                notifications_list.append(f'Your post "{post.title}" has been approved ✅')
            else:
                notifications_list.append(f'Your post "{post.title}" has been rejected ❌')

    return render(request, 'Account/notifications.html', {'notifications': notifications_list})



# ---------------- AJAX / API (stugum ete arden ka )----------------
def check_username(request):
    username = request.GET.get("username", "")
    exists = User.objects.filter(username=username).exists()
    return JsonResponse({"exists": exists})

def check_email(request):
    email = request.GET.get("email", "")
    exists = User.objects.filter(email=email).exclude(id=request.user.id).exists()
    return JsonResponse({"exists": exists})

def check_phone(request):
    phone = request.GET.get("phone", "")
    exists = Profile.objects.filter(phone=phone).exclude(user=request.user).exists()
    return JsonResponse({"exists": exists})

def check_id(request):
    vid = request.GET.get("verification_id", "")
    exists = Profile.objects.filter(verification_id=vid).exclude(user=request.user).exists()
    return JsonResponse({"exists": exists})
#-----------------------------------------------------------------------------------------------------------------
GOOGLE_API_KEY = 'AIzaSyD9KO1U7_6JxlBuCpiLju_K0tXwBM4ISWE'  # Move to settings.py for security

def calculate_distance(request):
    """
    Expects GET parameters:
    - user_lat
    - user_lng
    - dest_lat
    - dest_lng
    """
    user_lat = request.GET.get('user_lat')
    user_lng = request.GET.get('user_lng')
    dest_lat = request.GET.get('dest_lat')
    dest_lng = request.GET.get('dest_lng')

    if not all([user_lat, user_lng, dest_lat, dest_lng]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    url = (
        f"https://maps.googleapis.com/maps/api/distancematrix/json?"
        f"origins={user_lat},{user_lng}&destinations={dest_lat},{dest_lng}"
        f"&mode=driving&key={GOOGLE_API_KEY}"
    )

    response = requests.get(url)
    data = response.json()

    if data['status'] != 'OK':
        return JsonResponse({'error': 'Failed to calculate distance'}, status=500)

    distance_text = data['rows'][0]['elements'][0]['distance']['text']
    distance_value = data['rows'][0]['elements'][0]['distance']['value']  # in meters
    duration_text = data['rows'][0]['elements'][0]['duration']['text']

    return JsonResponse({
        'distance_text': distance_text,
        'distance_meters': distance_value,
        'duration_text': duration_text
    })

@login_required
def get_provinces(request, state_id):
    provinces = Province.objects.filter(state_id=state_id).order_by('name')
    data = [{'id': p.id, 'name': p.name} for p in provinces]
    return JsonResponse({'provinces': data})








@login_required
def task_applications(request, post_id):
    """View applications for a task (only for task owner)"""
    post = get_object_or_404(Post, id=post_id, user=request.user)
    applications = post.applications.select_related('applicant').all()
    
    return render(request, 'tasks/task_applications.html', {
        'post': post,
        'applications': applications
    })

@login_required
def assign_task(request, post_id, applicant_id):
    """Task owner assigns task to an applicant - FIXED"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    post = get_object_or_404(Post, id=post_id, user=request.user)
    applicant = get_object_or_404(User, id=applicant_id)
    
    # Check if applicant actually applied
    if not TaskApplication.objects.filter(post=post, applicant=applicant).exists():
        return JsonResponse({'success': False, 'error': 'User has not applied for this task'})
    
    # Check if task is still open
    if post.task_status != 'open':
        return JsonResponse({'success': False, 'error': 'Task is no longer open for assignment'})
    
    # Assign the task
    post.assigned_to = applicant
    post.task_status = 'in_progress'
    post.assigned_at = timezone.now()
    post.save()
    
    # Create notification for assigned user
    Notification.objects.create(
        user=applicant,
        message=f"You have been assigned to the task: '{post.title}'",
        post=post
    )
    
    # Create notification for other applicants
    other_applicants = TaskApplication.objects.filter(post=post).exclude(applicant=applicant)
    for application in other_applicants:
        Notification.objects.create(
            user=application.applicant,
            message=f"The task '{post.title}' has been assigned to another applicant",
            post=post
        )
    
    messages.success(request, f'Task assigned to {applicant.username}')
    return JsonResponse({'success': True})



@login_required
def complete_task(request, post_id):
    """Mark task as completed"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    post = get_object_or_404(Post, id=post_id, user=request.user)
    
    if post.task_status != 'in_progress':
        return JsonResponse({'success': False, 'error': 'Task is not in progress'})
    
    post.task_status = 'completed'
    post.completed_at = timezone.now()
    post.save()
    
    messages.success(request, 'Task marked as completed!')
    return JsonResponse({'success': True})




@login_required
def mark_incomplete(request, post_id):
    """Owner marks task as incomplete - triggers dispute if worker marked it completed"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    task = get_object_or_404(Post, id=post_id, user=request.user)
    
    if task.task_status not in ['in_progress', 'waiting_approval']:
        return JsonResponse({'success': False, 'error': 'Task is not in progress or waiting approval'})
    
    # Check if worker previously marked as completed
    if task.worker_completed_at and task.task_status == 'waiting_approval':
        # This is a dispute scenario - worker said completed, owner says incomplete
        dispute = TaskDispute.objects.create(
            post=task,
            dispute_type='worker_completed_owner_incomplete',
            initiated_by=request.user,
            other_party=task.assigned_to,
            reason=f"Owner marked task as incomplete after worker marked it completed. Worker completion time: {task.worker_completed_at}",
            status='pending'
        )
        
        # Change task status to under review
        task.task_status = 'under_review'
        task.save()
        
        # Notify admins
        admin_users = User.objects.filter(profile__role__in=['admin', 'superadmin'])
        for admin_user in admin_users:
            Notification.objects.create(
                user=admin_user,
                message=f"New dispute: Worker marked task '{task.title}' as completed but owner marked it incomplete. Dispute ID: {dispute.id}",
                post=task
            )
        
        # Notify worker
        if task.assigned_to:
            Notification.objects.create(
                user=task.assigned_to,
                message=f"The owner has marked your completed task '{task.title}' as incomplete. The case has been sent to admins for review.",
                post=task
            )
        
        return JsonResponse({
            'success': True, 
            'dispute_created': True,
            'message': 'Task marked as incomplete. A dispute has been created and sent to admins for review. The task is now under review.'
        })
    
    # Normal incomplete marking (no dispute)
    task.task_status = 'incomplete'
    task.save()
    
    # Notify worker if assigned
    if task.assigned_to:
        Notification.objects.create(
            user=task.assigned_to,
            message=f"The owner has marked task '{task.title}' as incomplete",
            post=task
        )
    
    return JsonResponse({'success': True, 'dispute_created': False})


@login_required
def worker_dispute_incomplete(request, post_id):
    """Worker disputes owner's incomplete marking"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    task = get_object_or_404(Post, id=post_id, assigned_to=request.user)
    
    if task.task_status != 'incomplete':
        return JsonResponse({'success': False, 'error': 'Task is not marked as incomplete'})
    
    # Create dispute
    dispute = TaskDispute.objects.create(
        post=task,
        dispute_type='worker_disputed_incomplete',
        initiated_by=request.user,
        other_party=task.user,
        reason=request.POST.get('reason', ''),
        status='pending'
    )
    
    # Change task status to under review
    task.task_status = 'under_review'
    task.save()
    
    # Notify admins
    admin_users = User.objects.filter(profile__role__in=['admin', 'superadmin'])
    for admin_user in admin_users:
        Notification.objects.create(
            user=admin_user,
            message=f"Worker disputed incomplete status for task '{task.title}'. Dispute ID: {dispute.id}",
            post=task
        )
    
    # Notify owner
    Notification.objects.create(
        user=task.user,
        message=f"The worker has disputed the incomplete status of task '{task.title}'. The case has been sent to admins for review.",
        post=task
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Dispute submitted successfully! The task is now under admin review.'
    })


@login_required
def contact_admin(request, post_id):
    """Either party can contact admin directly with evidence"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    task = get_object_or_404(Post, id=post_id)
    
    # Check if user is involved in the task
    if request.user not in [task.user, task.assigned_to]:
        return JsonResponse({'success': False, 'error': 'Not authorized'})
    
    message = request.POST.get('message', '').strip()
    if not message:
        return JsonResponse({'success': False, 'error': 'Message is required'})
    
    # Create dispute
    dispute = TaskDispute.objects.create(
        post=task,
        dispute_type='direct_message',
        initiated_by=request.user,
        other_party=task.assigned_to if request.user == task.user else task.user,
        reason=message,
        status='pending'
    )
    
    # Handle image upload
    if 'image' in request.FILES:
        image = request.FILES['image']
        # Create message with image
        DisputeMessage.objects.create(
            dispute=dispute,
            sender=request.user,
            message=message,
            image=image
        )
    else:
        # Create message without image
        DisputeMessage.objects.create(
            dispute=dispute,
            sender=request.user,
            message=message
        )
    
    # Change task status to under review if not already
    if task.task_status != 'under_review':
        task.task_status = 'under_review'
        task.save()
    
    # Notify admins
    admin_users = User.objects.filter(profile__role__in=['admin', 'superadmin'])
    for admin_user in admin_users:
        Notification.objects.create(
            user=admin_user,
            message=f"New admin message for task '{task.title}'. Dispute ID: {dispute.id}",
            post=task
        )
    
    return JsonResponse({
        'success': True,
        'message': 'Your message has been sent to admins. The task is now under review.'
    })


@login_required
def send_dispute_message(request, dispute_id):
    """Send additional messages in an existing dispute"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    dispute = get_object_or_404(TaskDispute, id=dispute_id)
    
    # Check if user is involved in the dispute
    if request.user not in [dispute.initiated_by, dispute.other_party]:
        return JsonResponse({'success': False, 'error': 'Not authorized'})
    
    message = request.POST.get('message', '').strip()
    if not message:
        return JsonResponse({'success': False, 'error': 'Message is required'})
    
    # Handle image upload
    image = None
    if 'image' in request.FILES:
        image = request.FILES['image']
    
    # Create message
    dispute_message = DisputeMessage.objects.create(
        dispute=dispute,
        sender=request.user,
        message=message,
        image=image
    )
    
    # Notify admins
    admin_users = User.objects.filter(profile__role__in=['admin', 'superadmin'])
    for admin_user in admin_users:
        Notification.objects.create(
            user=admin_user,
            message=f"New message in dispute #{dispute.id} for task '{dispute.post.title}'",
            post=dispute.post
        )
    
    return JsonResponse({
        'success': True,
        'message': 'Message sent successfully',
        'message_id': dispute_message.id
    })


@login_required
def get_dispute_messages(request, dispute_id):
    """Get all messages for a dispute"""
    dispute = get_object_or_404(TaskDispute, id=dispute_id)
    
    # Check if user is involved in the dispute or is admin
    if (request.user not in [dispute.initiated_by, dispute.other_party] and 
        not (hasattr(request.user, 'profile') and 
             request.user.profile.role in ['admin', 'superadmin'])):
        return JsonResponse({'success': False, 'error': 'Not authorized'})
    
    messages = dispute.messages.all().order_by('created_at')
    messages_data = []
    
    for msg in messages:
        messages_data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'sender_id': msg.sender.id,
            'message': msg.message,
            'image': msg.image.url if msg.image else None,
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_own_message': msg.sender == request.user
        })
    
    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'dispute_status': dispute.status
    })

def admin_dispute_detail(request, dispute_id):
    """
    View for admin to see dispute details
    """
    dispute = get_object_or_404(TaskDispute, id=dispute_id)
    
    # Get evidence for this dispute
    evidence = dispute.evidence.all()
    
    context = {
        'dispute': dispute,
        'evidence': evidence,
    }
    
    return render(request, 'admin/dispute_detail.html', context)

@admin_required
def resolve_dispute(request, dispute_id):
    """
    Handle admin decision on dispute
    """
    dispute = get_object_or_404(TaskDispute, id=dispute_id)
    
    if request.method == 'POST':
        decision = request.POST.get('decision')
        admin_notes = request.POST.get('admin_notes', '')
        
        if decision in ['completed', 'cancelled', 'refunded']:
            # Use the model method to resolve the dispute
            success = dispute.resolve_dispute(
                decision=decision,
                admin_user=request.user,
                notes=admin_notes
            )
            
            if success:
                # Success messages based on decision
                if decision == 'completed':
                    messages.success(
                        request, 
                        f'Dispute resolved: Work marked as completed. Payment released to {dispute.worker.username}.'
                    )
                elif decision == 'cancelled':
                    messages.success(
                        request,
                        f'Dispute resolved: Task cancelled. Refund processed for {dispute.post.user.username}.'
                    )
                elif decision == 'refunded':
                    messages.success(
                        request,
                        f'Dispute resolved: Full refund issued to {dispute.post.user.username}.'
                    )
            else:
                messages.error(request, 'Failed to resolve dispute. Please try again.')
            
            return redirect('admin_dispute_detail', dispute_id=dispute.id)
        else:
            messages.error(request, 'Invalid decision selected.')
    
    return redirect('admin_dispute_detail', dispute_id=dispute.id)

@admin_required
def reopen_dispute(request, dispute_id):
    """
    Reopen a resolved dispute
    """
    dispute = get_object_or_404(TaskDispute, id=dispute_id)
    
    if dispute.is_resolved:
        dispute.status = 'reopened'
        dispute.post.status = 'disputed'
        dispute.save()
        dispute.post.save()
        
        messages.success(request, f'Dispute #{dispute.id} has been reopened for review.')
    else:
        messages.warning(request, 'This dispute is already active.')
    
    return redirect('admin_dispute_detail', dispute_id=dispute.id)

@admin_required
def admin_user_detail(request, user_id):
    """
    View for admin to see user details
    """
    from django.contrib.auth.models import User
    from django.db.models import Q
    
    user = get_object_or_404(User, id=user_id)
    
    # Get user's disputes (both as worker and as post owner)
    user_disputes = TaskDispute.objects.filter(
        Q(post__user=user) | Q(worker=user)
    ).order_by('-created_at')
    
    # Get user's posts/tasks
    user_posts = Post.objects.filter(
        Q(user=user) | Q(assigned_worker=user)
    ).order_by('-created_at')
    
    context = {
        'user_profile': user,
        'user_disputes': user_disputes,
        'user_posts': user_posts,
    }
    
    return render(request, 'admin/user_detail.html', context)






@admin_required
def admin_disputes(request):
    """Admin view to see all disputes"""
    status_filter = request.GET.get('status', 'all')
    
    disputes = TaskDispute.objects.select_related(
        'post', 'initiated_by', 'other_party', 'resolved_by'
    ).all().order_by('-created_at')
    
    if status_filter != 'all':
        disputes = disputes.filter(status=status_filter)
    
    # Statistics
    total_disputes = disputes.count()
    pending_disputes = disputes.filter(status='pending').count()
    under_review_disputes = disputes.filter(status='under_review').count()
    resolved_disputes = disputes.filter(status='resolved').count()
    
    context = {
        'disputes': disputes,
        'total_disputes': total_disputes,
        'pending_disputes': pending_disputes,
        'under_review_disputes': under_review_disputes,
        'resolved_disputes': resolved_disputes,
        'current_status': status_filter,
        'page_title': 'Task Disputes'
    }
    
    return render(request, 'admin/disputes.html', context)

@admin_required
def dispute_detail(request, dispute_id):
    """Admin view for dispute details"""
    dispute = get_object_or_404(TaskDispute, id=dispute_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        resolution = request.POST.get('resolution', '')
        admin_notes = request.POST.get('admin_notes', '')
        
        if action == 'start_review':
            dispute.mark_under_review()
            messages.success(request, 'Dispute marked as under review.')
        
        elif action == 'resolve':
            if not resolution:
                messages.error(request, 'Resolution text is required.')
            else:
                dispute.resolve_dispute(request.user, resolution, admin_notes)
                
                # Notify both parties
                Notification.objects.create(
                    user=dispute.initiated_by,
                    message=f"Your dispute for task '{dispute.post.title}' has been resolved: {resolution}",
                    post=dispute.post
                )
                Notification.objects.create(
                    user=dispute.other_party,
                    message=f"The dispute for task '{dispute.post.title}' has been resolved: {resolution}",
                    post=dispute.post
                )
                
                messages.success(request, 'Dispute resolved successfully.')
        
        elif action == 'dismiss':
            dispute.status = 'dismissed'
            dispute.resolved_by = request.user
            dispute.resolution = 'Dispute dismissed by admin'
            dispute.admin_notes = admin_notes
            dispute.resolved_at = timezone.now()
            dispute.save()
            messages.info(request, 'Dispute dismissed.')
        
        return redirect('dispute_detail', dispute_id=dispute_id)
    
    # Get related information
    task_applications = TaskApplication.objects.filter(post=dispute.post)
    chat_messages = ChatMessage.objects.filter(
        Q(sender=dispute.initiated_by, recipient=dispute.other_party) |
        Q(sender=dispute.other_party, recipient=dispute.initiated_by)
    ).order_by('created_at')
    
    context = {
        'dispute': dispute,
        'task_applications': task_applications,
        'chat_messages': chat_messages,
        'page_title': f'Dispute #{dispute.id}'
    }
    
    return render(request, 'admin/dispute_detail.html', context)

@login_required
def submit_dispute_evidence(request, dispute_id):
    """Allow users to submit evidence for disputes"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    dispute = get_object_or_404(TaskDispute, id=dispute_id)
    
    # Check if user is involved in the dispute
    if request.user not in [dispute.initiated_by, dispute.other_party]:
        return JsonResponse({'success': False, 'error': 'Not authorized'})
    
    evidence_text = request.POST.get('evidence', '').strip()
    if not evidence_text:
        return JsonResponse({'success': False, 'error': 'Evidence text is required'})
    
    # Determine which evidence field to update
    if request.user == dispute.initiated_by:
        if dispute.initiated_by == dispute.post.user:  # Owner
            dispute.owner_evidence = evidence_text
        else:  # Worker
            dispute.worker_evidence = evidence_text
    else:  # Other party
        if request.user == dispute.post.user:  # Owner
            dispute.owner_evidence = evidence_text
        else:  # Worker
            dispute.worker_evidence = evidence_text
    
    dispute.save()
    
    # Notify admins
    admin_users = User.objects.filter(profile__role__in=['admin', 'superadmin'])
    for admin_user in admin_users:
        Notification.objects.create(
            user=admin_user,
            message=f"New evidence submitted for dispute #{dispute.id} on task '{dispute.post.title}'",
            post=dispute.post
        )
    
    return JsonResponse({'success': True, 'message': 'Evidence submitted successfully'})



@login_required
def cancel_task(request, post_id):
    """Cancel the task"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    post = get_object_or_404(Post, id=post_id, user=request.user)
    
    post.task_status = 'cancelled'
    post.assigned_to = None
    post.save()
    
    messages.info(request, 'Task cancelled')
    return JsonResponse({'success': True})

@login_required
def my_applications(request):
    """View user's task applications"""
    applications = TaskApplication.objects.filter(applicant=request.user).select_related('post')
    return render(request, 'tasks/my_applications.html', {'applications': applications})




# Add this model for notifications (add to models.py first)


# Update the apply_for_task view to create notifications
@login_required
def apply_for_task(request, post_id):
    """User applies for a task"""
    post = get_object_or_404(Post, id=post_id, status='approved')
    
    # Check if user already applied
    if TaskApplication.objects.filter(post=post, applicant=request.user).exists():
        messages.warning(request, 'You have already applied for this task.')
        return redirect('task_detail', post_id=post_id)
    
    # Check if user is applying to their own task
    if post.user == request.user:
        messages.error(request, 'You cannot apply to your own task.')
        return redirect('task_detail', post_id=post_id)
    
    if request.method == 'POST':
        message = request.POST.get('message', '')
        application = TaskApplication.objects.create(
            post=post,
            applicant=request.user,
            message=message
        )
        
        # CREATE NOTIFICATION FOR TASK OWNER
        Notification.objects.create(
            user=post.user,
            message=f"{request.user.username} applied for your task: '{post.title}'",
            post=post
        )
        
        messages.success(request, 'Application submitted successfully!')
        return redirect('task_detail', post_id=post_id)
    
    return render(request, 'tasks/apply_task.html', {'post': post})

# Update the notifications view
@login_required
def notifications(request):
    user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark as read when user views notifications
    user_notifications.update(is_read=True)
    
    return render(request, 'Account/notifications.html', {
        'notifications': user_notifications
    })

# Add notification count to context processor (optional)
def notification_count(request):
    if request.user.is_authenticated:
        return {
            'unread_notifications_count': Notification.objects.filter(
                user=request.user, is_read=False
            ).count()
        }
    return {}




# Add these views to your views.py


@login_required
def start_task(request, post_id):
    """Worker starts working on assigned task"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    task = get_object_or_404(Post, id=post_id, assigned_to=request.user)
    
    if task.task_status != 'in_progress':
        return JsonResponse({'success': False, 'error': 'Task is not in progress'})
    
    task.worker_started_at = timezone.now()
    task.save()
    
    return JsonResponse({'success': True})


@login_required
def worker_cancel_task(request, post_id):
    """Worker cancels the task"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    task = get_object_or_404(Post, id=post_id, assigned_to=request.user)
    
    if task.task_status != 'in_progress':
        return JsonResponse({'success': False, 'error': 'Task is not in progress'})
    
    task.task_status = 'cancelled'
    task.worker_cancelled_at = timezone.now()
    task.assigned_to = None
    task.save()
    
    # Create notification for task owner
    Notification.objects.create(
        user=task.user,
        message=f"{request.user.username} cancelled the task '{task.title}'",
        post=task
    )
    
    return JsonResponse({'success': True})

@login_required
def worker_mark_incomplete(request, post_id):
    """Worker marks task as incomplete"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    task = get_object_or_404(Post, id=post_id, assigned_to=request.user)
    
    if task.task_status != 'in_progress':
        return JsonResponse({'success': False, 'error': 'Task is not in progress'})
    
    task.task_status = 'incomplete'
    task.worker_incomplete_at = timezone.now()
    task.save()
    
    # Create notification for task owner
    Notification.objects.create(
        user=task.user,
        message=f"{request.user.username} marked your task '{task.title}' as incomplete",
        post=task
    )
    
    return JsonResponse({'success': True})


@login_required
def resubmit_task(request, post_id):
    """Resubmit an incomplete task to make it active again"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    post = get_object_or_404(Post, id=post_id, user=request.user)
    
    if post.task_status != 'incomplete':
        return JsonResponse({'success': False, 'error': 'Task is not incomplete'})
    
    # Reset task to open status
    post.task_status = 'open'
    post.assigned_to = None
    post.assigned_at = None
    post.completed_at = None
    post.cancelled_by_user = False
    post.cancellation_reason = None
    post.save()
    
    messages.success(request, 'Task resubmitted and is now open for applications!')
    return JsonResponse({'success': True})


@login_required
def myposts(request):
    """Combined view for user's posts and assigned tasks"""
    current_filter = request.GET.get('filter', 'all')
    view_type = request.GET.get('view', 'all')  # all, owner, worker
    
    # Get posts where user is owner
    owned_posts = Post.objects.filter(user=request.user).order_by('-created_at')
    
    # Get posts where user is assigned worker
    worker_tasks = Post.objects.filter(assigned_to=request.user, status='approved').order_by('-assigned_at')
    
    # Combine based on view type
    if view_type == 'owner':
        posts = owned_posts
        is_owner_view = True
    elif view_type == 'worker':
        posts = worker_tasks
        is_owner_view = False
    else:  # all
        # Combine both querysets
        owned_ids = list(owned_posts.values_list('id', flat=True))
        worker_ids = list(worker_tasks.values_list('id', flat=True))
        all_ids = list(set(owned_ids + worker_ids))
        posts = Post.objects.filter(id__in=all_ids).order_by('-created_at')
        is_owner_view = None
    
    # Filter based on task status
    if current_filter == 'all':
        posts = posts
    elif current_filter == 'active':
        posts = posts.filter(status='approved', task_status='open')
    elif current_filter == 'in_progress':
        posts = posts.filter(task_status='in_progress')
    elif current_filter == 'waiting_approval':
        posts = posts.filter(task_status='waiting_approval')
    elif current_filter == 'completed':
        posts = posts.filter(task_status='completed')
    elif current_filter == 'incomplete':
        posts = posts.filter(task_status='incomplete')
    elif current_filter == 'cancelled':
        posts = posts.filter(task_status='cancelled')
    elif current_filter == 'rejected':
        posts = posts.filter(status='rejected')
    elif current_filter == 'pending':
        posts = posts.filter(status='pending')
    elif current_filter == 'disputed':
        posts = posts.filter(Q(disputed_by_worker=True) | Q(disputed_by_owner=True))
    
    # Statistics
    total_owned = owned_posts.count()
    total_worker = worker_tasks.count()
    active_posts = owned_posts.filter(status='approved', task_status='open').count()
    in_progress_tasks = owned_posts.filter(task_status='in_progress').count()
    completed_tasks = owned_posts.filter(task_status='completed').count()
    incomplete_tasks = owned_posts.filter(task_status='incomplete').count()
    cancelled_tasks = owned_posts.filter(task_status='cancelled').count()
    
    # Worker statistics
    in_progress_worker = worker_tasks.filter(task_status='in_progress').count()
    waiting_approval_worker = worker_tasks.filter(task_status='waiting_approval').count()
    completed_worker = worker_tasks.filter(task_status='completed').count()
    
    return render(request, 'Account/myposts.html', {
        'posts': posts,
        'current_filter': current_filter,
        'view_type': view_type,
        'is_owner_view': is_owner_view,
        
        # Owner statistics
        'total_posts': total_owned,
        'active_posts': active_posts,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'incomplete_tasks': incomplete_tasks,
        'cancelled_tasks': cancelled_tasks,
        
        # Worker statistics
        'total_worker': total_worker,
        'in_progress_worker': in_progress_worker,
        'waiting_approval_worker': waiting_approval_worker,
        'completed_worker': completed_worker,
        
        # Combined
        'total_combined': total_owned + total_worker,
    })








# Add these new views for worker task workflow

@login_required
def worker_tasks(request):
    """View tasks assigned to the current user (worker) - FIXED"""
    current_filter = request.GET.get('filter', 'in_progress')
    
    # Get tasks assigned to current user with approved status
    assigned_tasks = Post.objects.filter(
        assigned_to=request.user, 
        status='approved'
    ).order_by('-assigned_at')
    
    # Filter based on task status
    if current_filter == 'in_progress':
        tasks = assigned_tasks.filter(task_status='in_progress')
    elif current_filter == 'waiting_approval':
        tasks = assigned_tasks.filter(task_status='waiting_approval')
    elif current_filter == 'completed':
        tasks = assigned_tasks.filter(task_status='completed')
    elif current_filter == 'incomplete':
        tasks = assigned_tasks.filter(task_status='incomplete')
    elif current_filter == 'cancelled':
        tasks = assigned_tasks.filter(task_status='cancelled')
    else:
        tasks = assigned_tasks  # Show all assigned tasks
    
    # Statistics for worker
    total_assigned = assigned_tasks.count()
    in_progress_count = assigned_tasks.filter(task_status='in_progress').count()
    completed_count = assigned_tasks.filter(task_status='completed').count()
    incomplete_count = assigned_tasks.filter(task_status='incomplete').count()
    cancelled_count = assigned_tasks.filter(task_status='cancelled').count()
    waiting_approval_count = assigned_tasks.filter(task_status='waiting_approval').count()
    
    return render(request, 'tasks/worker_tasks.html', {
        'tasks': tasks,
        'current_filter': current_filter,
        'total_assigned': total_assigned,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'incomplete_count': incomplete_count,
        'cancelled_count': cancelled_count,
        'waiting_approval_count': waiting_approval_count,
    })

@login_required
def worker_complete_task(request, post_id):
    """Worker marks task as completed - waits for owner approval"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    task = get_object_or_404(Post, id=post_id, assigned_to=request.user)
    
    if task.task_status != 'in_progress':
        return JsonResponse({'success': False, 'error': 'Task is not in progress'})
    
    # Change status to waiting for owner approval instead of directly completed
    task.task_status = 'waiting_approval'
    task.worker_completed_at = timezone.now()
    task.save()
    
    # Create notification for task owner
    Notification.objects.create(
        user=task.user,
        message=f"{request.user.username} has marked the task '{task.title}' as completed and is waiting for your approval",
        post=task
    )
    
    # Return data for review popup - worker rates owner
    response_data = {
        'success': True,
        'post_id': task.id,
        'owner_id': task.user.id,
        'owner_username': task.user.username,
        'task_title': task.title,
        'review_type': 'worker_to_owner'
    }
    
    messages.success(request, 'Task marked as completed! Waiting for owner approval.')
    return JsonResponse(response_data)

@login_required
def owner_approve_completion(request, post_id):
    """Post owner approves worker's completion"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    task = get_object_or_404(Post, id=post_id, user=request.user)
    
    if task.task_status != 'waiting_approval':
        return JsonResponse({'success': False, 'error': 'Task is not waiting for approval'})
    
    # Mark as fully completed
    task.task_status = 'completed'
    task.completed_at = timezone.now()
    task.save()
    
    # Create notification for worker
    if task.assigned_to:
        Notification.objects.create(
            user=task.assigned_to,
            message=f"The owner has approved your completion of the task '{task.title}'",
            post=task
        )
    
    # Return data for review popup - owner rates worker
    response_data = {
        'success': True,
        'post_id': task.id,
        'worker_id': task.assigned_to.id if task.assigned_to else None,
        'worker_username': task.assigned_to.username if task.assigned_to else None,
        'task_title': task.title,
        'review_type': 'owner_to_worker'
    }
    
    messages.success(request, 'Task completion approved!')
    return JsonResponse(response_data)

@login_required
def owner_complete_task(request, post_id):
    """Owner directly marks task as completed (without worker completion)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    task = get_object_or_404(Post, id=post_id, user=request.user)
    
    if task.task_status != 'in_progress':
        return JsonResponse({'success': False, 'error': 'Task is not in progress'})
    
    # Mark as completed
    task.task_status = 'completed'
    task.completed_at = timezone.now()
    task.save()
    
    # Create notification for worker
    if task.assigned_to:
        Notification.objects.create(
            user=task.assigned_to,
            message=f"The owner has marked the task '{task.title}' as completed",
            post=task
        )
    
    # Return data for review popup - owner rates worker
    response_data = {
        'success': True,
        'post_id': task.id,
        'worker_id': task.assigned_to.id if task.assigned_to else None,
        'worker_username': task.assigned_to.username if task.assigned_to else None,
        'task_title': task.title,
        'review_type': 'owner_to_worker'
    }
    
    messages.success(request, 'Task marked as completed!')
    return JsonResponse(response_data)

@csrf_exempt
@login_required
def submit_review(request):
    """Handle review submission with better error handling"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        data = json.loads(request.body)
        
        # Extract required fields
        post_id = data.get('post_id')
        reviewed_user_id = data.get('reviewed_user_id')
        review_type = data.get('review_type')
        rating = data.get('rating')
        comment = data.get('comment', '')
        
        # Validate required fields
        if not all([post_id, reviewed_user_id, review_type, rating]):
            return JsonResponse({
                'success': False, 
                'error': 'Missing required fields'
            })
        
        # Validate rating
        try:
            rating = int(rating)
            if not 1 <= rating <= 5:
                return JsonResponse({
                    'success': False,
                    'error': 'Rating must be between 1 and 5'
                })
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Rating must be a number'
            })
        
        # Get objects
        post = get_object_or_404(Post, id=post_id)
        reviewed_user = get_object_or_404(User, id=reviewed_user_id)
        
        # Verify the current user has permission to review
        if review_type == 'worker_to_owner':
            # Worker reviewing owner - check if current user is the assigned worker
            if post.assigned_to != request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'Only the assigned worker can review the owner'
                })
        elif review_type == 'owner_to_worker':
            # Owner reviewing worker - check if current user is the post owner
            if post.user != request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'Only the task owner can review the worker'
                })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid review type'
            })
        
        # Check if review already exists and update, or create new
        review, created = Review.objects.update_or_create(
            post=post,
            reviewer=request.user,
            review_type=review_type,
            defaults={
                'reviewed_user': reviewed_user,
                'rating': rating,
                'comment': comment,
                'is_verified': True
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Review submitted successfully' if created else 'Review updated successfully',
            'review_id': review.id,
            'action': 'created' if created else 'updated'
        })
        
    except IntegrityError as e:
        logger.error(f"IntegrityError in submit_review: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Review already exists for this task'
        })
    except Exception as e:
        logger.error(f"Unexpected error in submit_review: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })


@login_required
def check_review_status(request, post_id):
    """Check if reviews exist for a post"""
    post = get_object_or_404(Post, id=post_id)
    
    # Check if current user has pending reviews for this post
    pending_reviews = Review.objects.filter(
        post=post,
        reviewer=request.user,
        rating=0  # Not rated yet
    )
    
    reviews_data = []
    for review in pending_reviews:
        reviews_data.append({
            'id': review.id,
            'review_type': review.review_type,
            'reviewed_user_id': review.reviewed_user.id,
            'reviewed_username': review.reviewed_user.username,
        })
    
    return JsonResponse({
        'success': True,
        'has_pending_reviews': pending_reviews.exists(),
        'pending_reviews': reviews_data
    })




@login_required
def get_pending_reviews(request):
    """Get pending reviews for the current user"""
    pending_reviews = Review.objects.filter(
        reviewer=request.user,
        rating=0  # Not rated yet
    ).select_related('post', 'reviewed_user')
    
    reviews_data = []
    for review in pending_reviews:
        reviews_data.append({
            'id': review.id,
            'post_id': review.post.id,
            'post_title': review.post.title,
            'reviewed_user_id': review.reviewed_user.id,
            'reviewed_username': review.reviewed_user.username,
            'review_type': review.review_type,
            'created_at': review.created_at.isoformat()
        })
    
    return JsonResponse({'success': True, 'pending_reviews': reviews_data})


@login_required
def owner_reject_completion(request, post_id):
    """Post owner rejects worker's completion"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    task = get_object_or_404(Post, id=post_id, user=request.user)
    
    if task.task_status != 'waiting_approval':
        return JsonResponse({'success': False, 'error': 'Task is not waiting for approval'})
    
    # Send back to in progress
    task.task_status = 'in_progress'
    task.save()
    
    # Create notification for worker
    if task.assigned_to:
        Notification.objects.create(
            user=task.assigned_to,
            message=f"The owner has requested changes for the task '{task.title}'. Please continue working.",
            post=task
        )
    
    messages.warning(request, 'Completion rejected. Task sent back to worker.')
    return JsonResponse({'success': True})







@login_required
def dispute_task(request, post_id):
    """Worker disputes owner's incomplete marking"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    task = get_object_or_404(Post, id=post_id, assigned_to=request.user)
    
    if task.task_status != 'incomplete':
        return JsonResponse({'success': False, 'error': 'Task is not marked as incomplete'})
    
    task.disputed_by_worker = True
    task.dispute_reason = request.POST.get('reason', '')
    task.save()
    
    # Create notification for support team
    support_users = User.objects.filter(profile__role__in=['admin', 'support', 'superadmin'])
    for user in support_users:
        Notification.objects.create(
            user=user,
            message=f"Task '{task.title}' has been disputed by worker {request.user.username}",
            post=task
        )
    
    messages.success(request, 'Task disputed successfully! Support team will review the case.')
    return JsonResponse({'success': True})

@login_required
def owner_dispute_task(request, post_id):
    """Owner disputes worker's completion"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    task = get_object_or_404(Post, id=post_id, user=request.user)
    
    if task.task_status != 'waiting_approval':
        return JsonResponse({'success': False, 'error': 'Task is not waiting for approval'})
    
    task.disputed_by_owner = True
    task.dispute_reason = request.POST.get('reason', '')
    task.task_status = 'incomplete'
    task.save()
    
    # Create notification for support team
    support_users = User.objects.filter(profile__role__in=['admin', 'support', 'superadmin'])
    for user in support_users:
        Notification.objects.create(
            user=user,
            message=f"Task '{task.title}' has been disputed by owner {request.user.username}",
            post=task
        )
    
    # Notify worker
    if task.assigned_to:
        Notification.objects.create(
            user=task.assigned_to,
            message=f"The owner has disputed your completion of task '{task.title}'. Support team will review.",
            post=task
        )
    
    messages.success(request, 'Task disputed successfully! Support team will review the case.')
    return JsonResponse({'success': True})







@csrf_exempt
@login_required
def track_task_view(request, post_id):
    """Track when a user views a task details"""
    if request.method == 'POST':
        try:
            post = Post.objects.get(id=post_id)
            
            # Don't count views by the post owner
            if post.user != request.user:
                post.increment_views()
            
            return JsonResponse({
                'success': True, 
                'views_count': post.views_count
            })
            
        except Post.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Post not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})




def applications_count(request):
    if request.user.is_authenticated:
        # Count posts where user is owner and has at least 1 application
        user_posts_with_applications_count = Post.objects.filter(
            user=request.user,
            applications__isnull=False
        ).distinct().count()
    else:
        user_posts_with_applications_count = 0
    
    return {
        'user_posts_with_applications_count': user_posts_with_applications_count
    }


def base_context(request):
    if request.user.is_authenticated:
        user_posts_with_applications_count = Post.objects.filter(
            user=request.user
        ).annotate(
            applications_count=Count('applications')
        ).filter(
            applications_count__gt=0
        ).count()
    else:
        user_posts_with_applications_count = 0
    
    return {
        'user_posts_with_applications_count': user_posts_with_applications_count
    }





import secrets
import string
from django.core.mail import send_mail
from django.conf import settings
from .models import PasswordResetToken
from .forms import PasswordResetRequestForm, SetNewPasswordForm

def generate_reset_token():
    """Generate a secure random token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(50))

def password_reset_request(request):
    """Handle password reset requests"""
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            
            # Delete any existing tokens for this user
            PasswordResetToken.objects.filter(user=user).delete()
            
            # Create new token
            token = generate_reset_token()
            expires_at = timezone.now() + timedelta(hours=24)  # Token valid for 24 hours
            
            PasswordResetToken.objects.create(
                user=user,
                token=token,
                expires_at=expires_at
            )
            
            # Build reset URL
            reset_url = request.build_absolute_uri(
                f'/password-reset-confirm/{user.id}/{token}/'
            )
            
            # Send email
            try:
                send_mail(
                    'Password Reset Request',
                    f'Hello {user.username},\n\n'
                    f'You requested a password reset. Please click the link below to reset your password:\n\n'
                    f'{reset_url}\n\n'
                    f'This link will expire in 24 hours.\n\n'
                    f'If you didn\'t request this, please ignore this email.\n\n'
                    f'Best regards,\nYour Website Team',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                
                messages.success(request, 'Password reset instructions have been sent to your email.')
                return redirect('password_reset_done')
                
            except Exception as e:
                logger.error(f"Error sending password reset email: {e}")
                messages.error(request, 'Failed to send email. Please try again later.')
                
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'password_reset_request.html', {'form': form})

def password_reset_done(request):
    """Show confirmation that reset email was sent"""
    return render(request, 'password_reset_done.html')

def password_reset_confirm(request, user_id, token):
    """Handle password reset confirmation"""
    try:
        user = User.objects.get(id=user_id)
        reset_token = PasswordResetToken.objects.get(user=user, token=token)
        
        if not reset_token.is_valid():
            messages.error(request, 'Invalid or expired reset link.')
            return redirect('password_reset_request')
        
        if request.method == 'POST':
            form = SetNewPasswordForm(request.POST)
            if form.is_valid():
                # Set new password
                new_password = form.cleaned_data['new_password1']
                user.set_password(new_password)
                user.save()
                
                # Mark token as used
                reset_token.is_used = True
                reset_token.save()
                
                # Log the user in automatically
                login(request, user)
                
                messages.success(request, 'Your password has been reset successfully!')
                return redirect('password_reset_complete')
        else:
            form = SetNewPasswordForm()
        
        return render(request, 'password_reset_confirm.html', {
            'form': form,
            'user_id': user_id,
            'token': token
        })
        
    except (User.DoesNotExist, PasswordResetToken.DoesNotExist):
        messages.error(request, 'Invalid reset link.')
        return redirect('password_reset_request')

def password_reset_complete(request):
    """Show password reset complete page"""
    return render(request, 'password_reset_complete.html')




