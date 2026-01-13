from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")

urlpatterns = [
    path("", root_redirect),
    path("admin/", admin.site.urls),
    path("audits/", include("audits.urls")),
    path("", include("courses.urls")),
    path("accounts/", include("accounts.urls")),
]
