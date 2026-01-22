from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import render, redirect
from courses.services import is_company_user, assign_required_company_courses

def register(request):
    ...
    user = form.save()
    email = user.email or ""
    if is_company_user(email):
        assign_required_company_courses(user)
    ...


from .forms import RegisterForm

def register(request):
    user = form.save()
    email = user.email or ""
    if is_company_user(email):
        assign_required_company_courses(user)
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created. Welcome!")
            return redirect("dashboard")
    else:
        form = RegisterForm()

    return render(request, "registration/register.html", {"form": form})
