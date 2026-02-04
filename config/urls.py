# config/urls.py
import os
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import logout
from django.contrib.auth import views as auth_views
from django.http import FileResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import include, path, re_path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.static import serve as static_serve

from apps.core import views as core_views
from accounts import views as accounts_views


# ----------------------------
# Root routing
# ----------------------------
def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("/app/")
    return redirect("/accounts/login/")


# ----------------------------
# CSRF helper (should NOT require login)
# Ensures csrftoken cookie exists on the backend origin
# ----------------------------
@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"ok": True})


# ----------------------------
# Logout helper
# NOTE: Ideally logout should be POST, but since you're doing top-level nav logout,
# GET is acceptable here for your use case (just be aware of CSRF implications).
# ----------------------------
def logout_then_login(request):
    logout(request)
    return redirect("/accounts/login/")


# ----------------------------
# SPA handler (SERVE index.html at /app/ and /app/*)
# IMPORTANT: This does NOT redirect to /static/app/index.html
# ----------------------------
def spa(request):
    index_path = Path(settings.BASE_DIR) / "static" / "app" / "index.html"
    if not index_path.exists():
        # Helpful message if build output isn't present in Railway container
        return JsonResponse(
            {
                "error": "SPA index.html not found",
                "expected": str(index_path),
                "hint": "Ensure Vite build outputs to backend/static/app and collectstatic runs on deploy.",
            },
            status=500,
        )

    # Serve the file contents as the response for /app/ and any /app/* route
    return FileResponse(open(index_path, "rb"), content_type="text/html")


urlpatterns = [
    # Root
    path("", root_redirect),

    # API
    path("api/me/", core_views.me, name="api-me"),
    path("api/csrf/", csrf, name="api-csrf"),

    # Admin
    path("admin/", admin.site.urls),

    # Apps
    path("audits/", include("audits.urls")),
    path("", include("courses.urls")),

    # Auth
    path("accounts/register/", accounts_views.register, name="register"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("accounts/logout/", logout_then_login, name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),

    # Debug helpers
    path("debug/media-list/", core_views.debug_media_list),

    # SPA entry (canonical)
    path("app/", spa, name="spa"),
]

# SPA routing MUST be near the end
urlpatterns += [
    path("app", lambda r: redirect("/app/", permanent=False)),
    re_path(r"^app/.*$", spa),
]

# MEDIA serving:
# - In production: only if SERVE_MEDIA=1 (Railway demo)
# - In DEBUG: Django can serve it
SERVE_MEDIA = os.getenv("SERVE_MEDIA", "0") == "1"
if settings.DEBUG or SERVE_MEDIA:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", static_serve, {"document_root": settings.MEDIA_ROOT}),
    ]
