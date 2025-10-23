# core/views.py
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils.timezone import now
from django.conf import settings
import os, json, re
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import Profile
from .forms import CustomUserCreationForm, EmailOrUsernameAuthenticationForm

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

# ---------------- Registration / Login / Logout ----------------
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)

            # Ensure username is unique only if already taken
            original_username = user.username
            counter = 1
            while User.objects.filter(username=user.username).exists():
                user.username = f"{original_username}{counter}"
                counter += 1
            user.save()

            # Create Profile with extra fields
            profile = Profile.objects.create(
                user=user,
                full_name=form.cleaned_data.get('full_name'),
                phone=form.cleaned_data.get('phone'),
                verification_id=form.cleaned_data.get('verification_id')
            )

            # --- Fix: authenticate user to set backend ---
            authenticated_user = authenticate(username=user.username, password=form.cleaned_data.get('password1'))
            if authenticated_user is not None:
                login(request, authenticated_user)  # Now backend is set
            else:
                messages.error(request, "Սխալ ստեղծման ժամանակ: Խնդրում ենք փորձել կրկին.")
                return redirect('register')

            # JSON log for all registered users with full info
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

            # Check if username already exists in JSON and update
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

    # AJAX edit
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
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []

        # Find existing user entry
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

    # GET request
    return render(request, 'Account.html', {'profile': profile, 'user': request.user})

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
