# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import Profile
import re
from django.contrib.auth import authenticate
from django import forms
from .models import Post


PHONE_RE = re.compile(r'^0\d{8}$')  # 9 digits starting with 0

def make_unique_username(base_username):
    username = base_username
    counter = 0
    while User.objects.filter(username=username).exists():
        counter += 1
        username = f"{base_username}{counter}"
    return username

# ---------------- Registration Form ----------------
class CustomUserCreationForm(UserCreationForm):
    full_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Անուն Ազգանուն','class':'form-control'}), label='Անուն Ազգանուն')
    username = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Օգտանուն','class':'form-control'}), label='Օգտանուն')
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder':'you@example.com','class':'form-control'}), label='Էլ. հասցե')
    phone = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder':'09XXXXXXXX','class':'form-control'}), label='Հեռախոս')
    verification_id = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder':'ID կամ Ցուցական համար','class':'form-control'}), label='Վերբերյալ ID')

    class Meta:
        model = User
        fields = ['username','full_name','email','phone','verification_id','password1','password2']

    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name','').strip()
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
        phone = self.cleaned_data.get('phone','').strip()
        if not PHONE_RE.match(phone):
            raise ValidationError("Հեռախոսահամարը պետք է լինի ձևաչափով 0XXXXXXXX (9 թվանշին):")
        if Profile.objects.filter(phone=phone).exists():
            raise ValidationError("Այս հեռախոսահամարը արդեն օգտագործվում է։")
        return phone

    def clean_verification_id(self):
        vid = self.cleaned_data.get('verification_id','').strip()
        if not vid:
            raise ValidationError("ID-ը պարտադիր է։")
        if Profile.objects.filter(verification_id=vid).exists():
            raise ValidationError("Այս ID-ն արդեն օգտագործվում է։")
        return vid

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
                verification_id=self.cleaned_data.get('verification_id'),
                full_name=full_name
            )
        return user

# ---------------- Authentication Forms ----------------
class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Օգտանուն կամ էլ. հասցե'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Գաղտնաբառ'}))

class EmailOrUsernameAuthenticationForm(forms.Form):
    username = forms.CharField(label="Email or Username", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Email or Username'}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Password'}))

    def clean(self):
        username_or_email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username_or_email and password:
            user = authenticate(username=username_or_email,password=password)
            if not user:
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(username=user_obj.username,password=password)
                except User.DoesNotExist:
                    user = None
            if not user:
                raise forms.ValidationError("Սխալ էլ. հասցե/օգտագործանուն կամ գաղտնաբառ")
            self.user_cache = user
        return self.cleaned_data

    def get_user(self):
        return getattr(self,'user_cache',None)

# ---------------- Profile Update Form ----------------
class ProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class':'form-control'}))
    phone = forms.CharField(required=True, widget=forms.TextInput(attrs={'class':'form-control'}))
    verification_id = forms.CharField(required=True, widget=forms.TextInput(attrs={'class':'form-control'}))
    full_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class':'form-control'}))

    class Meta:
        model = Profile
        fields = ['full_name','phone','verification_id']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        # prefill email from User model
        self.fields['email'].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise ValidationError("Այս էլ. հասցեն արդեն օգտագործվում է։")
        return email

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if not PHONE_RE.match(phone):
            raise ValidationError("Հեռախոսը պետք է սկսվի 0-ով և ունենա 9 թվանշան")
        if Profile.objects.filter(phone=phone).exclude(user=self.user).exists():
            raise ValidationError("Այս հեռախոսահամարը արդեն օգտագործվում է")
        return phone

    def clean_verification_id(self):
        vid = self.cleaned_data['verification_id']
        if not re.match(r'^[A-Z0-9]+$', vid):
            raise ValidationError("Մեծատառ և նիշ, օրինակ ALO123")
        if Profile.objects.filter(verification_id=vid).exclude(user=self.user).exists():
            raise ValidationError("Այս ID-ն արդեն օգտագործվում է")
        return vid

    def save(self, commit=True):
        full_name = self.cleaned_data['full_name'].strip()
        first_name, last_name = full_name.split()[0], ' '.join(full_name.split()[1:])
        self.user.first_name = first_name
        self.user.last_name = last_name
        self.user.email = self.cleaned_data['email']
        if commit:
            self.user.save()
            super().save(commit=commit)
        return self.instance
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'image', 'description', 'price', 'category', 'state', 'province', 'location']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Վերնագիր', 'class':'input-field'}),
            'description': forms.Textarea(attrs={'placeholder': 'Նկարագրություն', 'class':'textarea-field'}),
            'price': forms.NumberInput(attrs={'placeholder': 'Դրամ', 'class':'input-field'}),
            'category': forms.Select(attrs={'class':'select-field'}),
            
            # --- ИСПРАВЛЕНИЯ ЗДЕСЬ ---
            'state': forms.Select(attrs={'class': 'select-field', 'id': 'state-select'}),
            'province': forms.Select(attrs={'class': 'select-field', 'id': 'province-select'}),
            # ---------------------------
            
            'location': forms.TextInput(attrs={'placeholder': 'Հասցե', 'class':'input-field'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the empty "---------" from Category
        self.fields['category'].empty_label = None
        self.fields['state'].empty_label = ''
        self.fields['province'].empty_label = None