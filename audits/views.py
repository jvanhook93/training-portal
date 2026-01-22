from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.utils.timezone import localtime

from courses.models import AssignmentCycle


# ------------------------------------------------------------------
# Certificate renderer hook
# ------------------------------------------------------------------
def render_certificate_pdf(
    *,
    full_name: str,
    course_title: str,
    completed_at,
    expires_at,
    certificate_id: str,
) -> bytes:
    """
    TEMPORARY certificate generator.

    Replace the body of this function with your real certificate
    PDF generator (ReportLab, WeasyPrint, etc).

    MUST return raw PDF bytes.
    """

    # ---- PLACEHOLDER CONTENT (valid deploy-safe stub) ----
    content = f"""
CERTIFICATE OF COMPLETION

Certificate ID: {certificate_id}

Name: {full_name}
Course: {course_title}

Completed On: {completed_at.strftime("%Y-%m-%d")}
Expires On: {expires_at.strftime("%Y-%m-%d") if expires_at else "N/A"}
""".strip()

    # This is NOT a real PDF.
    # Replace ASAP with your actual generator.
    return content.encode("utf-8")


# ------------------------------------------------------------------
# Certificate download endpoint
# ------------------------------------------------------------------
@login_required
def certificate_download(request, certificate_id: str):
    """
    Generate and download a certificate PDF.

    Rules:
    - Certificate must exist
    - Course must be completed
    - User must own the assignment OR be staff/auditor
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

    # Must be completed
    if not cycle.completed_at:
        raise Http404("Certificate not available")

    # Permission check
    user = request.user
    is_owner = cycle.assignment.assignee_id == user.id
    is_admin = user.is_staff or user.is_superuser
    can_audit = user.has_perm("courses.can_audit_certs")

    if not (is_owner or is_admin or can_audit):
        raise Http404("Not found")

    assignee = cycle.assignment.assignee
    course = cycle.assignment.course_version.course

    full_name = (
        assignee.get_full_name()
        or assignee.username
        or assignee.email
        or "User"
    ).strip()

    pdf_bytes = render_certificate_pdf(
        full_name=full_name,
        course_title=course.title,
        completed_at=localtime(cycle.completed_at),
        expires_at=localtime(cycle.expires_at) if cycle.expires_at else None,
        certificate_id=cycle.certificate_id,
    )

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="certificate-{cycle.certificate_id}.pdf"'
    )
    return response


@login_required
def audit_center(request):
    return HttpResponse("Audit Center – coming soon")