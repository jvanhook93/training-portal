import os
from io import BytesIO

from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.http import require_POST

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from .models import Assignment, AssignmentCycle, CourseVersion, VideoProgress


# ----------------------------
# Helpers
# ----------------------------

def _is_assigned_or_staff(user, cv: CourseVersion) -> bool:
    return user.is_staff or Assignment.objects.filter(assignee=user, course_version=cv).exists()


def _get_quiz(cv: CourseVersion):
    """
    Returns the Quiz for a CourseVersion if configured, else None.
    IMPORTANT: this assumes your Quiz model uses related_name="course_quiz"
    on the OneToOneField to CourseVersion.
    """
    return getattr(cv, "course_quiz", None)


# ----------------------------
# Training player + progress
# ----------------------------

@login_required
def my_training(request, course_version_id: int):
    cv = get_object_or_404(CourseVersion, id=course_version_id)

    if not _is_assigned_or_staff(request.user, cv):
        return HttpResponseForbidden("Not assigned to this training.")

    vp, _ = VideoProgress.objects.get_or_create(user=request.user, course_version=cv)

    quiz = _get_quiz(cv)
    quiz_required = bool(quiz and quiz.is_required)

    quiz_passed = request.session.get(f"quiz_passed_cv_{cv.id}", False)
    quiz_score = request.session.get(f"quiz_score_cv_{cv.id}", None)

    return render(
        request,
        "courses/training.html",
        {
            "cv": cv,
            "vp": vp,
            "quiz_required": quiz_required,
            "quiz_passed": quiz_passed,
            "quiz_score": quiz_score,
        },
    )


@require_POST
@login_required
def video_ping(request, course_version_id: int):
    cv = get_object_or_404(CourseVersion, id=course_version_id)

    if not _is_assigned_or_staff(request.user, cv):
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


# ----------------------------
# Dashboard
# ----------------------------

@login_required
def dashboard(request):
    assignments = (
        Assignment.objects
        .filter(assignee=request.user)
        .select_related("course_version", "course_version__course")
    )

    rows = []
    for a in assignments:
        cycle = a.cycles.first()  # ordering = ["-completed_at"] on AssignmentCycle
        days_remaining = None
        status_label = a.status

        if cycle:
            days_remaining = (cycle.expires_at.date() - now().date()).days

            if days_remaining < 0:
                status_label = "EXPIRED"
            elif days_remaining <= 30:
                status_label = "DUE SOON"
            else:
                status_label = "COMPLIANT"

        rows.append({
            "assignment": a,
            "cycle": cycle,
            "days_remaining": days_remaining,
            "status_label": status_label,
        })

    return render(request, "courses/dashboard.html", {"rows": rows})


# ----------------------------
# Completion
# ----------------------------

@require_POST
@login_required
def complete_course_version(request, course_version_id: int):
    cv = get_object_or_404(CourseVersion, id=course_version_id)

    if not _is_assigned_or_staff(request.user, cv):
        return HttpResponseForbidden("Not assigned to this training.")

    assignment = get_object_or_404(Assignment, assignee=request.user, course_version=cv)

    # Require video progress threshold
    vp = VideoProgress.objects.filter(user=request.user, course_version=cv).first()
    pct = vp.percent if vp else 0

    if pct < 90:
        messages.error(request, f"Watch at least 90% of the video to complete (currently {pct}%).")
        return redirect("my_training", course_version_id=cv.id)

    # Quiz gating (if configured + required)
    quiz = _get_quiz(cv)
    quiz_required = bool(quiz and quiz.is_required)

    quiz_passed = request.session.get(f"quiz_passed_cv_{cv.id}", False)
    quiz_score = request.session.get(f"quiz_score_cv_{cv.id}", None)

    if quiz_required and not quiz_passed:
        messages.error(request, "This training requires a quiz. Please pass the quiz before completion.")
        return redirect("take_quiz", course_version_id=cv.id)

    # Create a new completion cycle (history preserved)
    AssignmentCycle.objects.create(
        assignment=assignment,
        completed_at=now(),
        expires_at=now() + relativedelta(months=11),
        passed=True,
        score=quiz_score if quiz_required else None,
        # certificate_id is auto-generated by your model.save()
    )

    assignment.status = Assignment.Status.COMPLETED
    assignment.save()

    # Optional: clear quiz session gates once completed (keeps demo tidy)
    request.session.pop(f"quiz_score_cv_{cv.id}", None)
    request.session.pop(f"quiz_passed_cv_{cv.id}", None)

    messages.success(request, "Training marked complete. Certificate generated.")
    return redirect("dashboard")


# ----------------------------
# Certificates
# ----------------------------

@login_required
def download_certificate(request, certificate_id: str):
    """
    Generates a PDF certificate for the given certificate_id.
    Access:
      - owner, staff, managers (direct reports), or users with courses.can_audit_certs
    """
    try:
        cycle = (
            AssignmentCycle.objects
            .select_related(
                "assignment",
                "assignment__assignee",
                "assignment__course_version",
                "assignment__course_version__course",
            )
            .get(certificate_id=certificate_id)
        )
    except AssignmentCycle.DoesNotExist:
        raise Http404("Certificate not found")

    assignee = cycle.assignment.assignee

    is_owner = assignee.id == request.user.id
    is_staff = request.user.is_staff
    has_audit_perm = request.user.has_perm("courses.can_audit_certs")

    is_manager = False
    try:
        is_manager = assignee.userprofile.manager_id == request.user.id
    except Exception:
        is_manager = False

    if not (is_owner or is_staff or is_manager or has_audit_perm):
        raise Http404("Not found")

    # Build PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    margin = 0.5 * inch
    c.setLineWidth(3)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    # Logo
    logo_path = os.path.join(settings.BASE_DIR, "media", "branding", "integra_logo.png")
    if os.path.exists(logo_path):
        c.drawImage(
            logo_path,
            margin + 0.05 * inch,
            height - 1.25 * inch,
            width=2.1 * inch,
            height=0.75 * inch,
            preserveAspectRatio=True,
            mask="auto",
        )

    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(width / 2, height - 1.35 * inch, "Certificate of Completion")

    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height - 1.7 * inch, "This certifies that")

    full_name = assignee.get_full_name() or assignee.username
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height - 2.4 * inch, full_name)

    course_title = cycle.assignment.course_version.course.title
    version = cycle.assignment.course_version.version

    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height - 3.0 * inch, "has successfully completed")

    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 3.6 * inch, f"{course_title} (Version {version})")

    completed_date = cycle.completed_at.date().strftime("%B %d, %Y")
    expires_date = cycle.expires_at.date().strftime("%B %d, %Y")

    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 4.3 * inch, f"Completed: {completed_date}    |    Expires: {expires_date}")

    c.setFont("Helvetica", 12)
    c.drawString(margin + 0.2 * inch, margin + 0.35 * inch, f"Certificate ID: {cycle.certificate_id}")

    c.setLineWidth(1)
    left_x1, left_x2 = width * 0.18, width * 0.45
    right_x1, right_x2 = width * 0.55, width * 0.82
    sig_y = margin + 1.2 * inch

    c.line(left_x1, sig_y, left_x2, sig_y)
    c.line(right_x1, sig_y, right_x2, sig_y)

    c.setFont("Helvetica", 12)
    c.drawCentredString((left_x1 + left_x2) / 2, sig_y - 0.25 * inch, "Training Administrator")
    c.drawCentredString((right_x1 + right_x2) / 2, sig_y - 0.25 * inch, completed_date)

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="certificate_{cycle.certificate_id}.pdf"'
    return resp


# ----------------------------
# Quiz
# ----------------------------

@login_required
def take_quiz(request, course_version_id: int):
    cv = get_object_or_404(CourseVersion, id=course_version_id)

    if not _is_assigned_or_staff(request.user, cv):
        return HttpResponseForbidden("Not assigned to this training.")

    quiz = _get_quiz(cv)
    if not quiz:
        raise Http404("Quiz not configured for this course.")

    questions = quiz.questions.prefetch_related("choices").order_by("order", "id")
    return render(request, "courses/quiz.html", {"cv": cv, "quiz": quiz, "questions": questions})


@require_POST
@login_required
def submit_quiz(request, course_version_id: int):
    cv = get_object_or_404(CourseVersion, id=course_version_id)

    if not _is_assigned_or_staff(request.user, cv):
        return HttpResponseForbidden("Not assigned to this training.")

    quiz = _get_quiz(cv)
    if not quiz:
        raise Http404("Quiz not configured for this course.")

    questions = quiz.questions.prefetch_related("choices").order_by("order", "id")
    total = questions.count()

    if total == 0:
        messages.error(request, "Quiz has no questions configured.")
        return redirect("my_training", course_version_id=cv.id)

    correct = 0
    for q in questions:
        picked = request.POST.get(f"q{q.id}")
        if not picked:
            continue
        try:
            choice = q.choices.get(id=int(picked))
            if choice.is_correct:
                correct += 1
        except Exception:
            pass

    score = int((correct / total) * 100)
    passed = score >= cv.pass_score

    request.session[f"quiz_score_cv_{cv.id}"] = score
    request.session[f"quiz_passed_cv_{cv.id}"] = passed

    if passed:
        messages.success(request, f"Quiz passed! Score: {score}%")
        return redirect("my_training", course_version_id=cv.id)

    messages.error(request, f"Quiz failed. Score: {score}% (need {cv.pass_score}%)")
    return redirect("take_quiz", course_version_id=cv.id)
