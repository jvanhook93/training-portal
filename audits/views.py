# audits/views.py
from __future__ import annotations

import csv
from datetime import datetime
from typing import Optional

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.timezone import now

from courses.models import Assignment, AssignmentCycle

User = get_user_model()


def _parse_date(s: str) -> Optional[datetime.date]:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


@staff_member_required
def audit_center(request):
    """
    Audit Center rows:
    - One row per (user, assignment) and attaches the latest cycle (if any)
    - If a user exists but has no assignments, they won’t show (by design).
      If you want ALL users no matter what, tell me and I’ll tweak it.
    """

    q = (request.GET.get("q") or "").strip()
    course = (request.GET.get("course") or "").strip()
    status = (request.GET.get("status") or "").strip()
    start = (request.GET.get("start") or "").strip()
    end = (request.GET.get("end") or "").strip()
    export = (request.GET.get("export") or "").strip().lower()

    start_d = _parse_date(start) if start else None
    end_d = _parse_date(end) if end else None

    # Base query: assignments + course/version + assignee + cycles
    qs = (
        Assignment.objects
        .select_related("assignee", "course_version", "course_version__course")
        .prefetch_related("cycles")  # ordered by Meta ordering on AssignmentCycle (-completed_at)
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

    # Build rows
    rows = []
    for a in qs:
        # latest cycle (because ordering = ["-completed_at"])
        cycle = a.cycles.all().first() if hasattr(a, "cycles") else None

        # If date filters are set, filter based on completed_at
        if (start_d or end_d):
            if not cycle or not cycle.completed_at:
                continue
            cd = cycle.completed_at.date()
            if start_d and cd < start_d:
                continue
            if end_d and cd > end_d:
                continue

        # Status label logic based on expires_at
        status_label = "—"
        if cycle and cycle.completed_at and cycle.expires_at:
            days = (cycle.expires_at.date() - now().date()).days
            if days < 0:
                status_label = "EXPIRED"
            elif days <= 30:
                status_label = "DUE SOON"
            else:
                status_label = "COMPLIANT"

        if status:
            # status filter expects COMPLIANT / DUE SOON / EXPIRED
            if status_label != status:
                continue

        user_display = (
            (a.assignee.get_full_name() or "").strip()
            or a.assignee.email
            or a.assignee.username
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

    # CSV export
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

    # Permission banner flag (your template expects this)
    # You can later tighten this to "direct reports" logic if you want.
    can_audit_all = request.user.is_staff or request.user.is_superuser or request.user.has_perm("courses.can_audit_certs")

    return render(request, "audits/audit_center.html", {
        "rows": rows,
        "q": q,
        "course": course,
        "status": status,
        "start": start,
        "end": end,
        "can_audit_all": can_audit_all,
    })
