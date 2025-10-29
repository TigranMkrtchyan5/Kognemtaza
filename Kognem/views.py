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




def task_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    return render(request, 'task_detail.html', {'post': post})

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





# @database_sync_to_async
# def create_notification(message):
#     ChatNotification.objects.create(user=message['recipient_id'], message_id=message['id'])


# @login_required
# def chat_room(request, room_name,user_id):
#     other = get_object_or_404(User, pk=user_id)

#     # Ensure user cannot chat with banned users
#     if other.profile.is_banned:
#         messages.error(request, "Cannot chat with this user.")
#         return redirect("messages_list")

#     room_name = f"chat_{min(request.user.id, other.id)}_{max(request.user.id, other.id)}"

#     messages_qs = ChatMessage.objects.filter(
#         sender_id__in=[request.user.id, other.id],
#         recipient_id__in=[request.user.id, other.id]
#     ).order_by("created_at")

#     message_data = [m.to_dict() for m in messages_qs]

#     return render(request, 'chat/chat.html', {
#         "room_name": room_name,
#         "other": other,
#         "messages": message_data,
#     })


@login_required
def view_post(request, post_id):
    # Only allow user to view their own post
    post = get_object_or_404(Post, id=post_id, user=request.user)
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




@login_required
def get_provinces(request, state_id):
    provinces = Province.objects.filter(state_id=state_id).order_by('name')
    data = [{'id': p.id, 'name': p.name} for p in provinces]
    return JsonResponse({'provinces': data})

# ---------------- Admin Decorators ----------------
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

# ---------------- Admin Dashboard ----------------
@admin_required
def admin_dashboard(request):
    if not request.user.is_authenticated or request.user.profile.role not in ['admin', 'superadmin']:
        form = EmailOrUsernameAuthenticationForm()
        return render(request, "admin/login.html", {"form": form})
    
    # ИЗМЕНЕНИЕ: Фильтруем пользователей, чтобы показывать ТОЛЬКО НЕЗАБАНЕННЫХ
    # Если вы используете BanLog, то проверяем, что нет активных банов
    active_users = User.objects.select_related("profile").exclude(
        bans__active=True, 
        bans__end_date__gt=timezone.now()
    ).distinct()
    
    pending_posts = Post.objects.filter(status='pending').order_by("-created_at")
    
    
    return render(request, "admin/dashboard.html", {
        "users": active_users, # <-- ИСПОЛЬЗУЕМ ОТФИЛЬТРОВАННЫХ ПОЛЬЗОВАТЕЛЕЙ
        "posts": pending_posts,
        "current_user": request.user,
        "admin_roles": ["admin", "superadmin", "support"],  # optional for template
    })

def admin_dashboard_login(request):
    """Login view for the admin dashboard."""
    if request.user.is_authenticated:
        # If user is already logged in, redirect to dashboard
        return redirect('admin_dashboard')

    form = EmailOrUsernameAuthenticationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        if user.profile.role in ['admin', 'superadmin']:
            return redirect('admin_dashboard')
        else:
            # Logged in but not an admin
            return render(request, "admin/login.html", {
                "form": form,
                "error": "You are not authorized to view the admin dashboard."
            })

    return render(request, "admin/login.html", {"form": form})


@admin_required
def user_detail(request, user_id):
    try:
        target_user = User.objects.select_related('profile').get(pk=user_id)
        posts = Post.objects.filter(user=target_user).order_by('-created_at')  # Optional if posts exist
        current_user_role = request.user.profile.role

        # Restrict admin from seeing superadmin info
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


# ---------------- Admin User Actions ----------------
@admin_required
def banned_users(request):
    # ИЗМЕНЕНИЕ: Используем 'bans__active' и 'bans__end_date'
    banned_users_list = User.objects.filter(
        bans__active=True,  # <-- ИСПРАВЛЕНО
        bans__end_date__gt=timezone.now()
    ).distinct().select_related('profile').prefetch_related('bans') # <-- ИСПРАВЛЕНО
    
    # Создаем объект active_ban для шаблона
    for user in banned_users_list:
        try:
            # ИСПОЛЬЗУЕМ user.bans.filter()
            user.active_ban = user.bans.filter(active=True).order_by('-end_date').first()
        except AttributeError:
             user.active_ban = None 
    
    return render(request, 'admin/banned_users.html', {'banned_users': banned_users_list})

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

        end_date = timezone.datetime.fromisoformat(end_date_str)
        if timezone.is_naive(end_date):
            end_date = timezone.make_aware(end_date)

        # Logout user from all sessions
        for session in Session.objects.all():
            session_data = session.get_decoded()
            if str(session_data.get('_auth_user_id')) == str(user.id):
                session.delete()

        # Create active ban
        BanLog.objects.create(
            user=user,
            admin=request.user,
            reason=reason,
            end_date=end_date,
            active=True
        )

        # ❌ Set user inactive to prevent login
        user.is_active = False
        user.save()

        return JsonResponse({"success": True, "message": "User banned and logged out."})

    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Internal server error: {str(e)}"}, status=500)






@property
def is_banned(self):
    now = timezone.now()
    return self.user.bans.filter(active=True, end_date__gt=now).exists()



@csrf_exempt
@admin_required
def unban_user(request, user_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    try:
        user = User.objects.get(pk=user_id)

        # Deactivate all active bans
        user.bans.filter(active=True).update(active=False)

        # Restore user activity
        user.is_active = True
        user.save()

        return JsonResponse({"success": True, "message": f"User {user.username} successfully unbanned."})

    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Internal server error: {str(e)}"}, status=500)


#------------------------------------------------------------------------------------------------------------------------
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

        # Check permissions
        target_role = user_to_reset.profile.role
        requester_role = request.user.profile.role

        ROLE_POWER = {"superadmin": 3, "admin": 2, "support": 1, "user": 0}
        if ROLE_POWER.get(requester_role, 0) <= ROLE_POWER.get(target_role, 0) and requester_role != "superadmin":
            return JsonResponse({
                "success": False,
                "error": "You do not have permission to reset this user's password."
            }, status=403)

        # ✅ Read JSON body correctly
        data = json.loads(request.body.decode("utf-8"))
        new_password = data.get("password")

        if not new_password:
            return JsonResponse({"success": False, "error": "New password is required"}, status=400)

        # ✅ Set new password
        user_to_reset.set_password(new_password)
        user_to_reset.save()

        return JsonResponse({"success": True, "message": "Password reset successfully"})

    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
# ---------------- Admin Post Actions ----------------
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
        # 1. Находим пост
        post = Post.objects.get(pk=post_id)
        
        # 2. Читаем тело JSON для получения причины
        try:
            data = json.loads(request.body)
            rejection_reason = data.get('reason', '').strip()
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON format"}, status=400)

        # 3. Проверяем наличие причины (требуется для админа)
        if not rejection_reason:
            return JsonResponse({"success": False, "error": "Rejection reason is required"}, status=400)
            
        # 4. Обновляем статус и сохраняем причину
        post.status = 'rejected'
        post.rejection_reason = rejection_reason # <-- ДОБАВЛЕНО/ИСПРАВЛЕНО
        post.save()
        
        return JsonResponse({"success": True})
        
    except Post.DoesNotExist:
        return JsonResponse({"success": False, "error": "Post not found"}, status=404)
    except Exception as e:
        # Общая ошибка, если что-то пошло не так
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

    # Filters from GET parameters
    category_id = request.GET.get('category')
    state_id = request.GET.get('state')
    province_id = request.GET.get('province')

    # Get all approved posts, newest first
    approved_posts = Post.objects.filter(status='approved').order_by('-created_at')

    if category_id:
        approved_posts = approved_posts.filter(category_id=category_id)
    if state_id:
        approved_posts = approved_posts.filter(state_id=state_id)
    if province_id:
        approved_posts = approved_posts.filter(province_id=province_id)

    # Get all filter options
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








# ---------------- Registration / Login / Logout ----------------
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)

            # Ensure unique username
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
                role='user'  # Default role
            )

            # Authenticate to set backend
            authenticated_user = authenticate(username=user.username, password=form.cleaned_data.get('password1'))
            if authenticated_user:
                login(request, authenticated_user)
            else:
                messages.error(request, "Սխալ ստեղծման ժամանակ: Խնդրում ենք փորձել կրկին.")
                return redirect('register')

            # Update JSON log
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
                    try: data = json.load(f)
                    except json.JSONDecodeError: data = []

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
    Supports login via username or email.
    """
    if request.user.is_authenticated:
        return redirect('home')

    form = EmailOrUsernameAuthenticationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        now = timezone.now()

        # ✅ Deactivate expired bans automatically
        now = timezone.now()

        # Deactivate expired bans automatically
        user.bans.filter(active=True, end_date__lt=now).update(active=False)

        # Check for active ban
        active_ban = user.bans.filter(active=True, end_date__gt=now).first()
        if active_ban:
            messages.error(
                request,
                f"Ձեր հաշիվը արգելված է մինչև {active_ban.end_date.strftime('%Y-%m-%d %H:%M')}"
            )
            return redirect('login')


        # Log in the user
        login(request, user)

        # Get or create profile
        profile, _ = Profile.objects.get_or_create(user=user)

        messages.success(
            request,
            f"Բարի վերադարձ, {profile.full_name or user.username}!"
        )
        return redirect('home')

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
def myposts(request):
    posts = Post.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'Account/myposts.html', {'posts': posts})

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



# ---------------- AJAX / API ----------------
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

# ---------------- Admin / Moderator Views ----------------

@moderator_required
def review_posts(request):
    # Example placeholder for post approval logic
    return render(request, 'admin/review_posts.html')


@csrf_exempt
@admin_required
def delete_post(request, post_id):
    """
    Удаляет пост по его ID (используется на страницах Rejected/Approved/Pending).
    """
    if request.method == 'POST':
        try:
            # Находим пост. Используем get_object_or_404, если он не был импортирован.
            post_to_delete = Post.objects.get(pk=post_id)
            
            # В отличие от пользователей, здесь обычно не нужны сложные проверки ролей
            # Просто удаляем, если админ имеет доступ к этой функции.
            post_to_delete.delete()
            
            return JsonResponse({"success": True, "message": "Post deleted successfully."})
            
        except Post.DoesNotExist:
            return JsonResponse({"success": False, "error": "Post not found."}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Internal error: {str(e)}"}, status=500)

    return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)





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