import os
from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.utils.cache import add_never_cache_headers
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.staticfiles import finders


def me(request):
    """
    Session-auth JSON endpoint for the SPA.
    IMPORTANT: must always return JSON, never redirect.
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    u = request.user
    return JsonResponse(
        {
            "id": u.id,
            "username": u.username,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "is_staff": u.is_staff,
            "is_superuser": u.is_superuser,
        }
    )


@login_required(login_url="/accounts/login/")
@ensure_csrf_cookie
def react_app(request):
    """
    Serve the built React SPA index.html for /app/* routes.

    We locate app/index.html via Django staticfiles finders so it works in:
    - DEBUG (STATICFILES_DIRS)
    - production with collectstatic/whitenoise
    """
    index_path = finders.find("app/index.html")

    if not index_path or not os.path.exists(index_path):
        return HttpResponse(
            "React build not found. Expected static/app/index.html. "
            "Run the frontend build so it outputs into static/app/ (or is collected into staticfiles).",
            status=500,
            content_type="text/plain",
        )

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    # SAFETY NET:
    # If vite built with base="/" it will reference /assets/...
    # On Django it needs /static/app/assets/...
    html = html.replace('src="/assets/', 'src="/static/app/assets/')
    html = html.replace("src='/assets/", "src='/static/app/assets/")
    html = html.replace('href="/assets/', 'href="/static/app/assets/')
    html = html.replace("href='/assets/", "href='/static/app/assets/")

    # Vite svg when built to static/app
    html = html.replace('href="/vite.svg"', 'href="/static/app/vite.svg"')
    html = html.replace('src="/vite.svg"', 'src="/static/app/vite.svg"')

    resp = HttpResponse(html, content_type="text/html")
    add_never_cache_headers(resp)
    return resp


@staff_member_required
def debug_media_list(request):
    root = Path(settings.MEDIA_ROOT)
    folder = root / "training_videos"

    if not folder.exists():
        return JsonResponse(
            {"media_root": str(root), "folder": str(folder), "exists": False, "files": []}
        )

    files = []
    for p in sorted(folder.glob("*")):
        if p.is_file():
            files.append({"name": p.name, "size": p.stat().st_size})

    return JsonResponse(
        {"media_root": str(root), "folder": str(folder), "exists": True, "files": files}
    )
