import os
from django.conf import settings
from django.http import FileResponse, Http404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required(login_url="/accounts/login/")
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
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "is_staff": u.is_staff,
    })