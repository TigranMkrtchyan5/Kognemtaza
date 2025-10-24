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
from .models import Profile,Post,BanLog
from .forms import CustomUserCreationForm, EmailOrUsernameAuthenticationForm
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta

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
@login_required(login_url='/admin-dashboard/login/')
def admin_dashboard(request):
    """Dashboard content, only for Admins/SuperAdmins."""
    if request.user.profile.role not in ['admin', 'superadmin']:
        return render(request, "admin/login.html", {
            "form": EmailOrUsernameAuthenticationForm(),
            "error": "You are not authorized to view the admin dashboard."
        })

    users = User.objects.select_related('profile').all()
    posts = Post.objects.all().order_by('-created_at')
    return render(request, "admin/dashboard.html", {
        "users": users,
        "posts": posts,
        "current_user": request.user,
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
    # Get all users with active bans
    banned_users_list = User.objects.filter(
        bans__active=True,  # `bans` is related_name from BanLog
        bans__end_date__gt=timezone.now()  # only current bans
    ).distinct().select_related('profile')
    
    return render(request, 'admin/banned_users.html', {'banned_users': banned_users_list})


@csrf_exempt
@admin_required
def ban_user(request, user_id):
    if request.method == "POST":
        try:
            user = User.objects.get(pk=user_id)
            if user.profile.role == 'superadmin':
                return JsonResponse({"success": False, "error": "Cannot ban a superadmin"})
            
            data = json.loads(request.body)
            reason = data.get("reason")
            end_date = data.get("end_date")
            if not reason or not end_date:
                return JsonResponse({"success": False, "error": "Reason and end date required"})
            
            end_date = timezone.datetime.fromisoformat(end_date)
            
            BanLog.objects.create(
                user=user,
                admin=request.user,
                reason=reason,
                end_date=end_date,
                active=True
            )
            return JsonResponse({"success": True})
        except User.DoesNotExist:
            return JsonResponse({"success": False, "error": "User not found"})




@csrf_exempt
@admin_required
def unban_user(request, user_id):
    try:
        user = User.objects.get(pk=user_id)
        active_bans = BanLog.objects.filter(user=user, active=True)
        for ban in active_bans:
            ban.active = False
            ban.save()
        return JsonResponse({"success": True})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"})



#------------------------------------------------------------------------------------------------------------------------
@csrf_exempt
@admin_required
def delete_user(request, user_id):
    try:
        user_to_delete = User.objects.get(pk=user_id)
        if request.user.profile.role == 'admin' and user_to_delete.profile.role in ['admin', 'superadmin', 'support']:
            return JsonResponse({"success": False, "error": "Cannot delete this user"})
        user_to_delete.delete()
        return JsonResponse({"success": True})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"})


@csrf_exempt
@admin_required
def reset_password(request, user_id):
    try:
        user_to_reset = User.objects.get(pk=user_id)
        if request.user.profile.role == 'admin' and user_to_reset.profile.role in ['admin', 'superadmin', 'support']:
            return JsonResponse({"success": False, "error": "Cannot reset this user password"})
        new_password = "Temp1234"  # Or generate randomly
        user_to_reset.set_password(new_password)
        user_to_reset.save()
        return JsonResponse({"success": True, "new_password": new_password})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"})


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
        return JsonResponse({"success": False, "error": "Post not found"})

@csrf_exempt
@admin_required
def reject_post(request, post_id):
    try:
        post = Post.objects.get(pk=post_id)
        post.status = 'rejected'
        post.save()
        return JsonResponse({"success": True})
    except Post.DoesNotExist:
        return JsonResponse({"success": False, "error": "Post not found"})
    

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
    if request.method == "POST" and "guest" in request.POST:
        if request.user.is_authenticated:
            logout(request)
        return redirect("home")
    return render(request, "start.html")

def home(request):
    full_name = None
    if request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        full_name = profile.full_name or request.user.username
    return render(request, 'home.html', {'full_name': full_name})

def ashxatanq(request):
    return render(request, 'ashxatanq.html')

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
    if request.method == "POST":
        form = EmailOrUsernameAuthenticationForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            # Check banned status
            if hasattr(user, 'profile') and user.profile.is_banned:
                messages.error(request, "Ձեր հաշիվը արգելված է։")
                return redirect('login')
            login(request, user)
            profile, _ = Profile.objects.get_or_create(user=user)
            messages.success(request, f"Բարի վերադարձ, {profile.full_name or user.username}!")
            return redirect('home')
        else:
            messages.error(request, "Սխալ էլ. հասցե/օգտագործանուն կամ գաղտնաբառ")
    else:
        form = EmailOrUsernameAuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "Դու դուրս եկար համակարգից։")
    return redirect("start")

# ---------------- Account / Profile ----------------
@login_required
def Account(request):
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

    return render(request, 'Account.html', {'profile': profile, 'user': request.user})

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
@admin_required
def admin_dashboard(request):
    users = User.objects.all().select_related('profile')
    return render(request, 'admin/dashboard.html', {'users': users})

@moderator_required
def review_posts(request):
    # Example placeholder for post approval logic
    return render(request, 'admin/review_posts.html')
