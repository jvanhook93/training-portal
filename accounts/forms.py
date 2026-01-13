from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]

    def clean_first_name(self):
        v = (self.cleaned_data.get("first_name") or "").strip()
        if not v:
            raise forms.ValidationError("First name is required.")
        return v

    def clean_last_name(self):
        v = (self.cleaned_data.get("last_name") or "").strip()
        if not v:
            raise forms.ValidationError("Last name is required.")
        return v

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2")

    def clean_email(self):
        email = (self.cleaned_data["email"] or "").strip().lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        email = self.cleaned_data["email"].strip().lower()
        user.username = email          # ✅ username = email
        user.email = email

        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()

        if commit:
            user.save()
        return user