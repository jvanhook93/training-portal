# apps/core/views.py
import os
from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.utils.encoding import smart_str
from django.contrib.staticfiles import finders


@login_required
def me(request):
    u = request.user
    return JsonResponse({
        "id": u.id,
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "is_staff": u.is_staff,
        "is_superuser": u.is_superuser,
    })


@login_required(login_url="/accounts/login/")
def react_app(request):
    """
    Serve the built React SPA index.html for /app/*.

    Uses staticfiles finders so it works with:
    - DEBUG + STATICFILES_DIRS
    - production + collectstatic/whitenoise
    """
    index_path = finders.find("app/index.html")

    if not index_path or not os.path.exists(index_path):
        raise Http404("React build not found. Expected static/app/index.html")

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    # SAFETY NET: if index.html has /assets/... (wrong in Django),
    # rewrite to /static/app/assets/...
    html = html.replace('src="/assets/', 'src="/static/app/assets/')
    html = html.replace("src='/assets/", "src='/static/app/assets/")
    html = html.replace('href="/assets/', 'href="/static/app/assets/')
    html = html.replace("href='/assets/", "href='/static/app/assets/")

    # Optional: patch vite svg if referenced from root
    html = html.replace('href="/vite.svg"', 'href="/static/app/vite.svg"')
    html = html.replace('src="/vite.svg"', 'src="/static/app/vite.svg"')

    resp = HttpResponse(html, content_type="text/html; charset=utf-8")
    resp["Cache-Control"] = "no-store"
    return resp


@staff_member_required
def media_check(request):
    rel = request.GET.get("path", "")
    abs_path = os.path.join(settings.MEDIA_ROOT, rel)
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
            files.append({
                "name": p.name,
                "size": p.stat().st_size,
            })

    return JsonResponse({
        "media_root": str(root),
        "folder": str(folder),
        "exists": True,
        "files": files,
    })
