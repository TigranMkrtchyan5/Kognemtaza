from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User,Profile
from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.http import require_POST
# from django.contrib.auth.decorators import login_required
# from django.contrib.auth import login as auth_login, logout as auth_logout
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .forms import EmailOrUsernameAuthenticationForm
from django.http import HttpResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


def home(request):
    return render(request, 'home.html')

def start(request):
    if request.method == "POST" and "guest" in request.POST:
        if request.user.is_authenticated:
            logout(request)  # clear session
        return redirect("home")
    return render(request, "start.html")


def ashxatanq(request):
    return render(request, 'ashxatanq.html')

import json
import os
from django.utils.timezone import now
from django.conf import settings  # Для получения BASE_DIR

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Barov ekar")

            # ✅ Добавим запись в JSON
            user_data = {
                "username": user.username,
                "email": user.email,
                "date_joined": now().strftime("%Y-%m-%d %H:%M")
            }

            # Путь к файлу JSON
            json_path = os.path.join(settings.BASE_DIR, 'user_data.json')

            # Загрузка текущих данных, если файл существует
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        data = []
            else:
                data = []

            # Добавляем нового пользователя
            data.append(user_data)

            # Сохраняем обратно
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

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
            messages.success(request, f"Բարի վերադարձ, {user.username}!")
            return redirect('home')
        else:
            messages.error(request, "Սխալ էլեկտրոնային հասցե/ծածկանուն կամ գաղտնաբառ")
    else:
        form = EmailOrUsernameAuthenticationForm()
    return render(request, 'login.html', {'form': form})

# def logout_view(request):
#     auth_logout(request)
#     messages.info(request, "Դուq դուրս եկաք համակարգից։")
#     return redirect('home')

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("star")

# def logout_view(request):
#     if request.user.is_authenticated:
#         logout(request)
#     return redirect('start')
 

def Account(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        verification_id = request.POST.get('verification_id')

        # Update User
        request.user.username = username
        request.user.email = email
        request.user.save()

        # Update Profile
        profile.phone = phone
        profile.verification_id = verification_id
        profile.save()

        messages.success(request, "Ձեր տվյալները պահպանվել են:")
        return redirect('Account')

    return render(request, 'Account.html', {'profile': profile})


from django.http import JsonResponse

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def account_view(request):
    user = request.user

    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        field = request.POST.get("field")
        value = request.POST.get("value", "").strip()

        # SERVER-SIDE VALIDATION
        if field == "username" and len(value) < 3:
            return JsonResponse({"success": False, "error": "Անունը պարտադիր է, օրինակ Joe Doe"})
        if field == "email" and "@" not in value:
            return JsonResponse({"success": False, "error": "Սխալ էլ. հասցե, օրինակ you@example.com"})
        if field == "phone" and (not value.startswith("0") or len(value) != 9):
            return JsonResponse({"success": False, "error": "Հեռախոսը պետք է սկսվի 0-ով և ունենա 9 թվանշան"})
        if field == "verification_id" and not value.isupper():
            return JsonResponse({"success": False, "error": "Միայն մեծատառ լատինական տառեր, օրինակ ALO"})

        # SAVE TO USER OR PROFILE
        if field in ["username", "email"]:
            setattr(user, field, value)
            user.save()
        else:
            setattr(user.profile, field, value)
            user.profile.save()

        return JsonResponse({"success": True})

    # fallback normal page render
    # return render(request, "account.html", context)

import re

PHONE_RE = re.compile(r'^0\d{8}$')          # 9 digits, starts with 0
VERIFICATION_RE = re.compile(r'^[A-Z\s]+$') # Only capital letters and spaces


# def logout_view(request):
#     if request.user.is_authenticated:
#         logout(request)
#         return redirect('start') 
#     else:
#         return redirect('login')