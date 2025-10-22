# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import Profile
import re
from django.contrib.auth import authenticate

PHONE_RE = re.compile(r'^0\d{8}$')  # 9 digits starting with 0


def make_unique_username(base_username):
    username = base_username
    counter = 0
    while User.objects.filter(username=username).exists():
        counter += 1
        username = f"{base_username}{counter}"
    return username


class CustomUserCreationForm(UserCreationForm):
    full_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Անուն Ազգանուն', 'class': 'form-control'}),
        label='Անուն Ազգանուն'
    )
    username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Օգտանուն', 'class': 'form-control'}),
        label='Օգտանուն'
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'you@example.com', 'class': 'form-control'}),
        label='Էլ. հասցե'
    )
    phone = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '09XXXXXXXX', 'class': 'form-control'}),
        label='Հեռախոս'
    )
    verification_id = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'ID կամ Ցուցական համար', 'class': 'form-control'}),
        label='Վերբերյալ ID'
    )

    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'phone', 'verification_id', 'password1', 'password2']

    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name', '').strip()
        if len(full_name.split()) < 2:
            raise ValidationError("Մուտքագրեք և անունը, և ազգանունը: (Օր․՝ Վարդան Պետրոսյան)")
        return full_name

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise ValidationError("Այս օգտանունը արդեն օգտագործվում է։")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Այս էլ. հասցեն արդեն գրանցված է։")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not PHONE_RE.match(phone):
            raise ValidationError("Հեռախոսահամարը պետք է լինի ձևաչափով 0XXXXXXXX (9 թվանշին):")
        return phone

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password1') or ''
        if pw:
            if len(pw) < 5:
                self.add_error('password1', ValidationError("Գաղտնաբառը պետք է պարունակի առնվազն 5 նիշ։"))
            if not any(ch.isupper() for ch in pw):
                self.add_error('password1', ValidationError("Գաղտնաբառը պետք է պարունակի առնվազն մեկ մեծատառ։"))
        return cleaned

    def save(self, commit=True):
        full_name = self.cleaned_data.get('full_name').strip()
        first_name, last_name = full_name.split()[0], ' '.join(full_name.split()[1:])

        username = self.cleaned_data.get('username')
        if not username:
            base_username = slugify(full_name.replace(' ', '_')) or 'user'
            username = make_unique_username(base_username)

        user = super(UserCreationForm, self).save(commit=False)
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.email = self.cleaned_data.get('email')

        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                phone=self.cleaned_data.get('phone'),
                verification_id=self.cleaned_data.get('verification_id')
            )
        return user


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Օգտանուն կամ էլ. հասցե'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Գաղտնաբառ'})
    )


class EmailOrUsernameAuthenticationForm(forms.Form):
    username = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email or Username'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

    def clean(self):
        username_or_email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username_or_email and password:
            # First try by username
            user = authenticate(username=username_or_email, password=password)
            if not user:
                # Try by email
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None

            if not user:
                raise forms.ValidationError("Սխալ էլ. հասցե/օգտագործանուն կամ գաղտնաբառ")

            self.user_cache = user

        return self.cleaned_data

    def get_user(self):
        return getattr(self, 'user_cache', None)
