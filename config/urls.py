from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.conf import settings

# ✅ needed for serving media without DEBUG
from django.views.static import serve

from apps.core import views as core_views
from accounts import views as accounts_views
from apps.core.views import react_app


# -------------------
# Root redirect
# -------------------
def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("/app/")
    return redirect("/accounts/login/")


# -------------------
# CSRF bootstrap endpoint (used by SPA)
# -------------------
@ensure_csrf_cookie
@login_required
def csrf(request):
    return JsonResponse({"ok": True})


# -------------------
# Logout handler (GET + POST safe)
# -------------------
def logout_then_login(request):
    logout(request)
    return redirect("/accounts/login/")


urlpatterns = [
    # Root
    path("", root_redirect),

    # -------------------
    # API
    # -------------------
    path("api/me/", core_views.me, name="api-me"),
    path("api/csrf/", csrf, name="api-csrf"),

    # -------------------
    # Admin
    # -------------------
    path("admin/", admin.site.urls),

    # -------------------
    # App modules
    # -------------------
    path("audits/", include("audits.urls")),
    path("", include("courses.urls")),

    # -------------------
    # Auth
    # -------------------
    path("accounts/register/", accounts_views.register, name="register"),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("accounts/logout/", logout_then_login, name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),

    # -------------------
    # SPA routing
    # -------------------
    # Redirect /app -> /app/
    path("app", lambda r: redirect("/app/", permanent=False)),

    # Optional debug endpoint (your existing one)
    path("debug/media-check/", core_views.media_check),

    # ✅ Serve MEDIA on Railway (demo/dev). Do NOT use for real prod PHI/PII.
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),

    # React SPA (keep LAST so it doesn't swallow /media/)
    re_path(r"^app/.*$", react_app),
]
