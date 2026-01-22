# apps/core/views.py
import os
from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.staticfiles import finders


@login_required
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)

    u = request.user
    return JsonResponse({
        "id": u.id,
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "is_staff": u.is_staff,
        "is_superuser": u.is_superuser,
    })


@staff_member_required
def media_check(request):
    rel = request.GET.get("path", "")
    abs_path = os.path.join(str(settings.MEDIA_ROOT), rel)
    return JsonResponse({
        "media_root": str(settings.MEDIA_ROOT),
        "requested": rel,
        "exists": os.path.exists(abs_path),
        "abs_path": abs_path,
    })


@staff_member_required
def debug_media_list(request):
    root = Path(settings.MEDIA_ROOT)
    folder = root / "training_videos"

    if not folder.exists():
        return JsonResponse({
            "media_root": str(root),
            "folder": str(folder),
            "exists": False,
            "files": [],
        })

    files = []
    for p in sorted(folder.glob("*")):
        if p.is_file():
            files.append({"name": p.name, "size": p.stat().st_size})

    return JsonResponse({
        "media_root": str(root),
        "folder": str(folder),
        "exists": True,
        "files": files,
    })


@login_required(login_url="/accounts/login/")
@ensure_csrf_cookie
def react_app(request):
    """
    Serves the built React index.html for any /app/* route.
    Works in DEBUG and in production with collectstatic/whitenoise.
    """
    index_path = finders.find("app/index.html")

    if not index_path or not os.path.exists(index_path):
        return HttpResponse(
            "React build not found. Expected static/app/index.html. "
            "Build frontend so it outputs into backend/static/app/",
            status=500,
            content_type="text/plain",
        )

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Safety net: patch root /assets -> Django static path
    html = html.replace('src="/assets/', 'src="/static/app/assets/')
    html = html.replace("src='/assets/", "src='/static/app/assets/")
    html = html.replace('href="/assets/', 'href="/static/app/assets/')
    html = html.replace("href='/assets/", "href='/static/app/assets/")

    resp = HttpResponse(html, content_type="text/html")
    resp["Cache-Control"] = "no-store"
    return resp


def me(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401
        )

    u = request.user
    return JsonResponse({
        "id": u.id,
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "is_staff": u.is_staff,
        "is_superuser": u.is_superuser,
    })