# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import Profile
import re

PHONE_RE = re.compile(r'^0\d{8}$') # sksuma 0 , hetevic 8 nish(tvanshan)

def make_unique_username(base_username):
    
    
    # username y sarquma unique , orinak ete 2 hat Tigran Mkrtchyan grancvi
    # Meky linelua Tigran-Mkrtchyan1 myusy Tigran-Mkrtchyan2...
    
    username = base_username
    counter = 0
    while User.objects.filter(username=username).exists():
        counter += 1
        username = f"{base_username}{counter}"
    return username

class CustomUserCreationForm(UserCreationForm):
    full_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Անուն Ազգանուն', 'class':'form-control'}),
        label='Անուն Ազգանուն'
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'you@example.com', 'class':'form-control'}),
        label='Էլ. հասցե'
    )
    phone = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '09XXXXXXXX', 'class':'form-control'}),
        label='Հեռախոս'
    )
    verification_id = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'ID կամ Ցուցական համար', 'class':'form-control'}),
        label='Վերբերյալ ID'
    )

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'verification_id', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data.get('full_')
        if User.objects.filter(username=username).exists():
            raise ValidationError("Այս օգտանունը արդեն օգտագործվում է։")
        return username

    
    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name', '').strip()
        # partadruma 2 bar prabelov ORINAK ABUL LUBA (arajin + erkrord)
        if len(full_name.split()) < 2:
            raise ValidationError("Մուտքագրեք և անունը, և ազգանունը: (Օր․՝ Վարդան Պետրոսյան)")
        return full_name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Այս էլ. հասցեն արդեն գրանցված է։")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        PHONE_RE = re.compile(r'^0\d{8}$')
        if not PHONE_RE.match(phone):
            raise ValidationError("Հեռախոսահամարը պետք է լինի ձևաչափով 0XXXXXXXX (9 թվանշին):")
        return phone

    def clean(self):
        cleaned = super().clean()
      
      
        # gaxtnabari stugum minimum 5 nish
        pw = cleaned.get('password1') or ''
        if pw:
            if len(pw) < 5:
                self.add_error('password1', ValidationError("Գաղտնաբառը պետք է պարունակի առնվազն 5 նիշ։"))
            if not any(ch.isupper() for ch in pw):
                self.add_error('password1', ValidationError("Գաղտնաբառը պետք է պարունակի առնվազն մեկ մեծատառ։"))
        return cleaned

    
    
    def save(self, commit=True):
        #username a sarqum
        full_name = self.cleaned_data.get('full_name', '').strip()
        # En unique usernamna taki gcikov sarqum
        base = slugify(full_name.replace(' ', '_'))
        if not base:
            base = slugify(full_name) or 'user'
        username = make_unique_username(base)

       
       
        # lriv anuny kisuma 2 masi
        parts = full_name.split()
        first_name = parts[0]
        last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

        user = super(UserCreationForm, self).save(commit=False)  # chi kanchum UserCreationForm.save miangamic
        user.username = username
        user.email = self.cleaned_data.get('email')
        user.first_name = first_name
        user.last_name = last_name

        if commit:
            user.save()
            # sarquma Profile
            Profile.objects.create(
                user=user,
                phone=self.cleaned_data.get('phone'),
                verification_id=self.cleaned_data.get('verification_id')
            )
        else:
            # if not commit, still attach profile info to user instance for later use
            self._profile_data = {
                'phone': self.cleaned_data.get('phone'),
                'verification_id': self.cleaned_data.get('verification_id')
            }
        return user


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Օգտանուն կամ էլլ.հասցե'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Գաղտնաբառ'}))

    class Meta:
        model = User
        fields = ['username', 'password']

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

class EmailOrUsernameAuthenticationForm(forms.Form):
    identifier = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email or Username'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

    def clean(self):
        identifier = self.cleaned_data.get('identifier')
        password = self.cleaned_data.get('password')

        if identifier and password:
            # usernamae ov a man galis 
            user = authenticate(username=identifier, password=password)
            if not user:
                # emailov user a man galis
                try:
                    user_obj = User.objects.get(email=identifier)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None

            if user is None:
                raise forms.ValidationError("Invalid username/email or password")

            self.user_cache = user

        return self.cleaned_data

    def get_user(self):
        return getattr(self, 'user_cache', None)
    
    