import os
from django.conf import settings
from pathlib import Path
from django.http import HttpResponse
from django.http import FileResponse, Http404
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie

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

@login_required(login_url="/accounts/login/")
def react_app(request):
    index_path = os.path.join(settings.BASE_DIR, "static", "app", "index.html")
    if not os.path.exists(index_path):
        raise Http404("React build not found. Build frontend and copy to static/app.")
    return FileResponse(open(index_path, "rb"))


@login_required(login_url="/accounts/login/")
@ensure_csrf_cookie
def react_app(request):
    index_path = os.path.join(settings.BASE_DIR, "static", "app", "index.html")
    if not os.path.exists(index_path):
        raise Http404("React build not found. Build frontend and copy to static/app.")
    return FileResponse(open(index_path, "rb"))


def me(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401
        )

    u = request.user
    return JsonResponse({
    "id": request.user.id,
    "username": request.user.username,
    "first_name": request.user.first_name,
    "last_name": request.user.last_name,
    "is_staff": request.user.is_staff,
    "is_superuser": request.user.is_superuser,
    })


def react_app(request):
    index_path = Path(settings.BASE_DIR) / "static" / "app" / "index.html"
    if not index_path.exists():
        return HttpResponse(
            "React build not found. Run: cd frontend && npm run build",
            status=500
        )
    return HttpResponse(index_path.read_text(encoding="utf-8"))


@staff_member_required
def debug_media_list(request):
    # List files under MEDIA_ROOT/training_videos
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