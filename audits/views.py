from datetime import datetime
import csv

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils.timezone import now

from courses.models import AssignmentCycle


def _parse_date(s: str):
    """Parse YYYY-MM-DD to date. Returns None if invalid/empty."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


@login_required
def audit_center(request):
    """
    Audit Center: search AssignmentCycles and download certs.

    Access:
      - staff OR users with courses.can_audit_certs: can see all users
      - otherwise, managers see only direct reports (plus themselves)
      - everyone else: forbidden
    """
    q = (request.GET.get("q") or "").strip()
    course = (request.GET.get("course") or "").strip()
    status = (request.GET.get("status") or "").strip()  # COMPLIANT / EXPIRED / DUE SOON / ""
    start = _parse_date(request.GET.get("start") or "")
    end = _parse_date(request.GET.get("end") or "")
    export = (request.GET.get("export") or "").strip()  # "csv" to export

    today = now().date()

    can_audit_all = request.user.is_staff or request.user.has_perm("courses.can_audit_certs")

    # Manager check: does anyone have request.user as their manager?
    is_manager = False
    if not can_audit_all:
        is_manager = AssignmentCycle.objects.filter(
            assignment__assignee__userprofile__manager_id=request.user.id
        ).exists()

    if not (can_audit_all or is_manager):
        return HttpResponseForbidden("Not authorized to access the Audit Center.")

    cycles = (
        AssignmentCycle.objects
        .select_related(
            "assignment",
            "assignment__assignee",
            "assignment__course_version",
            "assignment__course_version__course",
        )
        .all()
    )

    # Restrict non-auditors to their direct reports (plus themselves)
    if not can_audit_all:
        cycles = cycles.filter(
            Q(assignment__assignee__userprofile__manager_id=request.user.id) |
            Q(assignment__assignee_id=request.user.id)
        )

    # Search
    if q:
        cycles = cycles.filter(
            Q(assignment__assignee__username__icontains=q) |
            Q(assignment__assignee__email__icontains=q) |
            Q(assignment__assignee__first_name__icontains=q) |
            Q(assignment__assignee__last_name__icontains=q) |
            Q(assignment__course_version__course__code__icontains=q) |
            Q(assignment__course_version__course__title__icontains=q) |
            Q(assignment__course_version__version__icontains=q) |
            Q(certificate_id__icontains=q)
        )

    if course:
        cycles = cycles.filter(assignment__course_version__course__code__icontains=course)

    if start:
        cycles = cycles.filter(completed_at__date__gte=start)
    if end:
        cycles = cycles.filter(completed_at__date__lte=end)

    # Only DB-filter for COMPLIANT/EXPIRED. We'll do DUE SOON precisely in Python.
    if status == "COMPLIANT":
        cycles = cycles.filter(expires_at__date__gte=today)
    elif status == "EXPIRED":
        cycles = cycles.filter(expires_at__date__lt=today)

    cycles = cycles.order_by("-completed_at")[:500]

    def compute_status(expires_date):
        days_remaining = (expires_date - today).days
        if days_remaining < 0:
            return "EXPIRED", days_remaining
        if days_remaining <= 30:
            return "DUE SOON", days_remaining
        return "COMPLIANT", days_remaining

    # CSV export
    if export.lower() == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="audit_export.csv"'
        w = csv.writer(resp)
        w.writerow([
            "User", "Course Code", "Course Title", "Version",
            "Completed", "Expires", "Status", "Days Remaining", "Certificate ID"
        ])

        for c in cycles:
            expires_date = c.expires_at.date()
            status_label, days_remaining = compute_status(expires_date)

            # Safe pulls
            a = c.assignment
            assignee = getattr(a, "assignee", None)
            cv = getattr(a, "course_version", None)
            course_obj = getattr(cv, "course", None) if cv else None

            user_val = getattr(assignee, "username", "") or getattr(assignee, "email", "") or "-"
            code_val = getattr(course_obj, "code", "") if course_obj else "-"
            title_val = getattr(course_obj, "title", "") if course_obj else "-"
            version_val = getattr(cv, "version", "") if cv else "-"

            w.writerow([
                user_val,
                code_val,
                title_val,
                version_val,
                c.completed_at.date().isoformat(),
                expires_date.isoformat(),
                status_label,
                days_remaining,
                c.certificate_id,
            ])
        return resp

    # Build rows for template (this is what your template expects)
    rows = []
    for c in cycles:
        expires_date = c.expires_at.date()
        status_label, days_remaining = compute_status(expires_date)

        # Apply DUE SOON filter precisely here
        if status == "DUE SOON" and status_label != "DUE SOON":
            continue

        a = c.assignment
        assignee = getattr(a, "assignee", None)
        cv = getattr(a, "course_version", None)
        course_obj = getattr(cv, "course", None) if cv else None

        user_display = getattr(assignee, "username", "") or getattr(assignee, "email", "") or "-"
        if course_obj:
            code = getattr(course_obj, "code", "") or ""
            title = getattr(course_obj, "title", "") or ""
            course_display = (f"{code} - {title}".strip(" -")) or "-"
        else:
            course_display = "-"

        version_display = getattr(cv, "version", "") if cv else "-"

        rows.append({
            "cycle": c,
            "status_label": status_label,
            "days_remaining": days_remaining,
            "user_display": user_display,
            "course_display": course_display,
            "version_display": version_display,
        })

    return render(
        request,
        "audits/audit_center.html",
        {
            "rows": rows,
            "q": q,
            "course": course,
            "status": status,
            "start": request.GET.get("start") or "",
            "end": request.GET.get("end") or "",
            "today": today,
            "can_audit_all": can_audit_all,
            "result_count": len(rows),
        },
    )
