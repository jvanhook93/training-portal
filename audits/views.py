# audits/views.py
import os
from io import BytesIO

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.timezone import localtime

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from courses.models import Assignment, AssignmentCycle


User = get_user_model()


# -----------------------------------------------------------------------------
# AUDIT CENTER
# -----------------------------------------------------------------------------
def audit_center(request):
    """
    Simple audit center:
    - Shows all users (optionally filtered by search)
    - Includes their assignments and latest completion cycle per assignment
    """
    q = (request.GET.get("q") or "").strip()

    users_qs = User.objects.all().order_by("username", "last_name", "first_name")
    if q:
        # basic search across common fields
        users_qs = users_qs.filter(
            # use icontains to match partials
            # (no OR import needed; Django allows multiple kwargs with | only via Q objects,
            # so we do a simple fallback: filter by username OR email OR name)
        )
        # Use Q objects properly:
        from django.db.models import Q
        users_qs = users_qs.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )

    # Prefetch assignments + course/version + cycles
    assignments_qs = (
        Assignment.objects
        .select_related("course_version", "course_version__course")
        .prefetch_related("cycles")  # cycles already ordered by Meta ordering = ["-completed_at"]
        .order_by("-assigned_at")
    )

    users = (
        users_qs
        .prefetch_related(Prefetch("assignments", queryset=assignments_qs))
    )

    # This expects you have a template. If you don’t, I can give you one.
    return render(request, "audits/audit_center.html", {"users": users, "q": q})


# -----------------------------------------------------------------------------
# CERTIFICATE DOWNLOAD (generate on demand)
# -----------------------------------------------------------------------------
@login_required
def certificate_download(request, certificate_id: str):
    """
    Download a completion certificate by certificate_id.
    Access:
      - owner OR staff/superuser OR has courses.can_audit_certs
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

    # Permission: owner OR staff/superuser OR audits permission
    if not (
        request.user.is_staff
        or request.user.is_superuser
        or request.user.has_perm("courses.can_audit_certs")
        or cycle.assignment.assignee_id == request.user.id
    ):
        raise Http404("Not found")

    if not cycle.completed_at:
        raise Http404("Course not completed")

    assignee = cycle.assignment.assignee
    full_name = (assignee.get_full_name() or assignee.username or assignee.email or "User").strip()

    course_title = cycle.assignment.course_version.course.title
    version = cycle.assignment.course_version.version

    completed_at = localtime(cycle.completed_at)
    expires_at = localtime(cycle.expires_at) if cycle.expires_at else None

    # --- Build PDF (ReportLab) ---
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    margin = 0.5 * inch
    c.setLineWidth(3)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    # Logo (optional)
    logo_path = os.path.join(str(getattr(cycle.assignment.course_version, "id", "")), "")  # no-op; keeps linter calm
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "media", "branding", "integra_logo.png")
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

    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height - 2.4 * inch, full_name)

    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height - 3.0 * inch, "has successfully completed")

    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 3.6 * inch, f"{course_title} (Version {version})")

    completed_date = completed_at.date().strftime("%B %d, %Y")
    expires_date = expires_at.date().strftime("%B %d, %Y") if expires_at else "—"

    c.setFont("Helvetica", 14)
    c.drawCentredString(
        width / 2,
        height - 4.3 * inch,
        f"Completed: {completed_date}    |    Expires: {expires_date}"
    )

    c.setFont("Helvetica", 12)
    c.drawString(margin + 0.2 * inch, margin + 0.35 * inch, f"Certificate ID: {cycle.certificate_id}")

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="certificate-{cycle.certificate_id}.pdf"'
    return resp
