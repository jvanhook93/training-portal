# audits/views.py
from __future__ import annotations

import csv
from datetime import datetime
from io import BytesIO
from typing import Optional

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.timezone import localtime, now

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from courses.models import Assignment, AssignmentCycle


def _parse_date(s: str) -> Optional[datetime.date]:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


@staff_member_required
def audit_center(request):
    q = (request.GET.get("q") or "").strip()
    course = (request.GET.get("course") or "").strip()
    status = (request.GET.get("status") or "").strip()
    start = (request.GET.get("start") or "").strip()
    end = (request.GET.get("end") or "").strip()
    export = (request.GET.get("export") or "").strip().lower()

    start_d = _parse_date(start) if start else None
    end_d = _parse_date(end) if end else None

    qs = (
        Assignment.objects
        .select_related("assignee", "course_version", "course_version__course")
        .prefetch_related("cycles")
        .order_by("assignee__username", "course_version__course__code", "-assigned_at")
    )

    if course:
        qs = qs.filter(course_version__course__code__icontains=course)

    if q:
        qs = qs.filter(
            Q(assignee__username__icontains=q)
            | Q(assignee__email__icontains=q)
            | Q(assignee__first_name__icontains=q)
            | Q(assignee__last_name__icontains=q)
            | Q(course_version__course__title__icontains=q)
            | Q(course_version__course__code__icontains=q)
            | Q(cycles__certificate_id__icontains=q)
        ).distinct()

    rows = []
    for a in qs:
        cycle = a.cycles.all().first() if hasattr(a, "cycles") else None

        if start_d or end_d:
            if not cycle or not cycle.completed_at:
                continue
            cd = cycle.completed_at.date()
            if start_d and cd < start_d:
                continue
            if end_d and cd > end_d:
                continue

        status_label = "—"
        if cycle and cycle.completed_at and cycle.expires_at:
            days = (cycle.expires_at.date() - now().date()).days
            if days < 0:
                status_label = "EXPIRED"
            elif days <= 30:
                status_label = "DUE SOON"
            else:
                status_label = "COMPLIANT"

        if status and status_label != status:
            continue

        assignee = a.assignee
        user_display = (
            (assignee.get_full_name() or "").strip()
            or assignee.email
            or assignee.username
        )

        course_display = f"{a.course_version.course.code} - {a.course_version.course.title}"
        version_display = a.course_version.version

        rows.append({
            "assignment": a,
            "cycle": cycle,
            "user_display": user_display,
            "course_display": course_display,
            "version_display": version_display,
            "status_label": status_label,
        })

    if export == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="audit_export.csv"'
        w = csv.writer(resp)
        w.writerow(["User", "Course", "Version", "Completed", "Expires", "Status", "Certificate ID"])
        for r in rows:
            c = r["cycle"]
            w.writerow([
                r["user_display"],
                r["course_display"],
                r["version_display"],
                c.completed_at.date().isoformat() if c and c.completed_at else "",
                c.expires_at.date().isoformat() if c and c.expires_at else "",
                r["status_label"],
                c.certificate_id if c else "",
            ])
        return resp

    can_audit_all = (
        request.user.is_staff
        or request.user.is_superuser
        or request.user.has_perm("courses.can_audit_certs")
    )

    return render(request, "audits/audit_center.html", {
        "rows": rows,
        "q": q,
        "course": course,
        "status": status,
        "start": start,
        "end": end,
        "can_audit_all": can_audit_all,
    })


@login_required
def certificate_download(request, certificate_id: str):
    """
    Download a completion certificate by certificate_id.
    This matches audits/urls.py: views.certificate_download
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

    # Permission: owner OR staff/superuser OR audit permission
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

    # Build PDF (ReportLab)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    margin = 0.5 * inch
    c.setLineWidth(3)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

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
    c.drawCentredString(width / 2, height - 4.3 * inch, f"Completed: {completed_date}    |    Expires: {expires_date}")

    c.setFont("Helvetica", 12)
    c.drawString(margin + 0.2 * inch, margin + 0.35 * inch, f"Certificate ID: {cycle.certificate_id}")

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="certificate-{cycle.certificate_id}.pdf"'
    return resp
