# config/urls.py
import os

from django.contrib import admin
from django.contrib.auth import logout
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path, re_path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.views.static import serve as static_serve

from apps.core import views as core_views
from accounts import views as accounts_views
from apps.core.views import react_app


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("/app/")
    return redirect("/accounts/login/")


@ensure_csrf_cookie
@login_required
def csrf(request):
    return JsonResponse({"ok": True})


def logout_then_login(request):
    logout(request)
    return redirect("/accounts/login/")


urlpatterns = [
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
]

# SPA routing MUST be near the end
urlpatterns += [
    path("app", lambda r: redirect("/app/", permanent=False)),
    re_path(r"^app/.*$", react_app),
]

# MEDIA serving:
# - In production: only if SERVE_MEDIA=1 (Railway demo)
# - In DEBUG: Django can serve it
SERVE_MEDIA = os.getenv("SERVE_MEDIA", "0") == "1"
if settings.DEBUG or SERVE_MEDIA:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", static_serve, {"document_root": settings.MEDIA_ROOT}),
    ]

# (Optional) allow local dev convenience for MEDIA if you want
# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
