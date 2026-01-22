# audits/views.py
from io import BytesIO

from django.contrib.auth.decorators import login_required, permission_required, staff_member_required
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.timezone import localtime

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from courses.models import AssignmentCycle

@staff_member_required
def audit_center(request):
    return HttpResponse("Audit Center (placeholder)", content_type="text/plain")

@login_required
def audit_center(request):
    """
    Minimal page so audits/urls.py can import it.
    You can replace this later with your real audit UI.
    """
    # If you don't have a template yet, you can return a simple HttpResponse instead.
    return HttpResponse("Audit Center")


def _render_certificate_pdf(*, full_name: str, course_title: str, version: str, completed_at, expires_at, certificate_id: str) -> bytes:
    """
    Generates a real PDF (ReportLab) so downloads work immediately.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(letter))
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

    completed_str = completed_at.date().strftime("%B %d, %Y") if completed_at else "—"
    expires_str = expires_at.date().strftime("%B %d, %Y") if expires_at else "—"

    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 4.3 * inch, f"Completed: {completed_str}    |    Expires: {expires_str}")

    c.setFont("Helvetica", 12)
    c.drawString(margin + 0.2 * inch, margin + 0.35 * inch, f"Certificate ID: {certificate_id}")

    c.showPage()
    c.save()

    pdf = buf.getvalue()
    buf.close()
    return pdf


@login_required
def certificate_download(request, certificate_id: str):
    """
    Download a completion certificate by certificate_id.
    User must own the assignment cycle OR be staff/superuser OR have courses.can_audit_certs
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

    # Permission: owner OR staff/superuser OR has audit perm
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

    cv = cycle.assignment.course_version
    course_title = cv.course.title
    version = cv.version

    completed_at = localtime(cycle.completed_at)
    expires_at = localtime(cycle.expires_at) if cycle.expires_at else None

    pdf_bytes = _render_certificate_pdf(
        full_name=full_name,
        course_title=course_title,
        version=version,
        completed_at=completed_at,
        expires_at=expires_at,
        certificate_id=cycle.certificate_id,
    )

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="certificate-{cycle.certificate_id}.pdf"'
    return resp
