from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static

from apps.core import views as core_views
from accounts import views as accounts_views
from apps.core.views import react_app


def logout_then_login(request):
    # Works for GET or POST, no template needed.
    logout(request)
    return redirect("/accounts/login/")


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("/app")
    return redirect("/accounts/login/")


@ensure_csrf_cookie
@login_required
def csrf(request):
    return JsonResponse({"ok": True})


urlpatterns = [
    # --- Root ---
    path("", root_redirect),

    # --- Admin MUST be early so nothing else can intercept it ---
    path("admin/", admin.site.urls),

    # --- Auth / Accounts ---
    path("accounts/register/", accounts_views.register, name="register"),
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
    path("accounts/", include("django.contrib.auth.urls")),

    # --- API ---
    path("api/me/", core_views.me, name="api-me"),
    path("accounts/logout/", logout_then_login, name="logout"),
    path("api/csrf/", csrf, name="api-csrf"),

    # --- Other apps ---
    path("audits/", include("audits.urls")),

    # --- React SPA (ONLY /app) ---
    # Matches /app and anything under it: /app, /app/, /app/whatever
    re_path(r"^app(?:/.*)?$", react_app),

    # --- Courses (kept at root) ---
    # IMPORTANT: This stays LAST so it can't swallow /admin or /accounts
    path("", include("courses.urls")),
]

# Media in dev (fine to keep)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
