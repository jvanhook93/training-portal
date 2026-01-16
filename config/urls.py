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


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("/app")
    return redirect("login")


@ensure_csrf_cookie
@login_required
def csrf(request):
    return JsonResponse({"ok": True})


def logout_then_login(request):
    # allow GET logout (and POST too)
    logout(request)
    return redirect("/accounts/login/")


urlpatterns = [
    path("", root_redirect),

    path("api/me/", core_views.me, name="api-me"),
    path("admin/", admin.site.urls),
    path("audits/", include("audits.urls")),
    path("", include("courses.urls")),
    path("api/csrf/", csrf, name="api-csrf"),

    path("accounts/register/", accounts_views.register, name="register"),

    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),

    # ✅ THIS is the fix
    path("accounts/logout/", logout_then_login, name="logout"),

    path("accounts/", include("django.contrib.auth.urls")),

    re_path(r"^app(?:/.*)?$", react_app),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
