from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from apps.core import views as core_views
from accounts import views as accounts_views
from apps.core.views import react_app


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


urlpatterns = [
    path("", root_redirect),

    path("api/me/", core_views.me, name="api-me"),
    path("admin/", admin.site.urls),
    path("audits/", include("audits.urls")),
    path("", include("courses.urls")),
    path("api/", include("courses.urls")),

    # Registration (your real POST-handling view)
    path("accounts/register/", accounts_views.register, name="register"),

    # Auth (use your custom login template)
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(next_page="/accounts/login/"),
        name="logout",
    ),

    # Django built-in auth routes (password reset, etc.)
    path("accounts/", include("django.contrib.auth.urls")),

    # React SPA
    re_path(r"^app(?:/.*)?$", react_app),
]
