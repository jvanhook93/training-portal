# accounts/views.py
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import render, redirect

from .forms import RegisterForm

# IMPORTANT: keep these imports here (top) only if they are safe.
# If you ever see import-related crashes, move them inside the POST success block.
from courses.services import is_company_user, assign_required_company_courses


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # ✅ Company-domain auto assignment AFTER user exists
            email = (user.email or "").strip().lower()
            try:
                if is_company_user(email):
                    assign_required_company_courses(user)
            except Exception:
                # Don't brick registration if assignment logic fails
                # (Optional) log this if you have logging configured
                pass

            login(request, user)
            messages.success(request, "Account created. Welcome!")
            return redirect("/app/")  # or: return redirect("dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegisterForm()

    # ✅ Make sure this template exists
    return render(request, "registration/register.html", {"form": form})
