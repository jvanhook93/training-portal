from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static

from apps.core import views as core_views
from accounts import views as accounts_views
from apps.core.views import react_app
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


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
        auth_views.LoginView.as_view(
            template_name="accounts/login.html"
        ),
        name="login",
    ),

    path(
        "accounts/logout/",
        logout_then_login,
        name="logout",
    ),

    # keep Django auth URLs (password reset, etc.)
    path("accounts/", include("django.contrib.auth.urls")),

    # -------------------
    # SPA routing
    # -------------------

    # IMPORTANT: redirect /app → /app/
    path("app", lambda r: redirect("/app/", permanent=False)),

    # React SPA (must be LAST)
    re_path(r"^app/.*$", react_app),
]


# -------------------
# Media (dev only)
# -------------------
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
