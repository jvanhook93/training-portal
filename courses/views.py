from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import CourseVersion, Assignment, VideoProgress


@login_required
def my_training(request, course_version_id: int):
    cv = get_object_or_404(CourseVersion, id=course_version_id)

    # Basic authorization: user must be assigned this course version
    is_assigned = Assignment.objects.filter(assignee=request.user, course_version=cv).exists()
    if not is_assigned and not request.user.is_staff:
        return HttpResponseForbidden("Not assigned to this training.")

    vp, _ = VideoProgress.objects.get_or_create(user=request.user, course_version=cv)

    return render(request, "courses/training.html", {"cv": cv, "vp": vp})


@require_POST
@login_required
def video_ping(request, course_version_id: int):
    cv = get_object_or_404(CourseVersion, id=course_version_id)

    is_assigned = Assignment.objects.filter(assignee=request.user, course_version=cv).exists()
    if not is_assigned and not request.user.is_staff:
        return HttpResponseForbidden("Not assigned to this training.")

    try:
        watched_seconds = int(request.POST.get("watched_seconds", "0"))
        total_seconds = int(request.POST.get("total_seconds", "0"))
        percent = int(request.POST.get("percent", "0"))
    except ValueError:
        return JsonResponse({"ok": False, "error": "Invalid numbers"}, status=400)

    percent = max(0, min(100, percent))

    vp, _ = VideoProgress.objects.get_or_create(user=request.user, course_version=cv)
    if vp.started_at is None:
        vp.started_at = timezone.now()

    vp.watched_seconds = max(vp.watched_seconds, watched_seconds)
    vp.total_seconds = max(vp.total_seconds, total_seconds)
    vp.percent = max(vp.percent, percent)

    if vp.percent >= 95 and vp.completed_at is None:
        vp.completed_at = timezone.now()

    vp.save()

    return JsonResponse({"ok": True, "percent": vp.percent, "completed": vp.completed_at is not None})
