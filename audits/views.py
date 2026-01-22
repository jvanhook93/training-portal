# audits/views.py
from io import BytesIO

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.timezone import localtime

from courses.models import AssignmentCycle


@staff_member_required
def audit_center(request):
    # Minimal placeholder so /audits/ loads and your import stops crashing.
    # You can flesh this out later.
    return render(request, "audits/audit_center.html", {})


@login_required
def certificate_download(request, certificate_id: str):
    """
    Download a completion certificate by certificate_id.
    User must own the assignment cycle OR be staff/superuser OR have courses.can_audit_certs.
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

    # Permission: owner OR staff/superuser OR has audits permission
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

    # --- Generate PDF using your existing ReportLab style ---
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas

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

    completed_str = completed_at.date().strftime("%B %d, %Y")
    expires_str = expires_at.date().strftime("%B %d, %Y") if expires_at else "—"

    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 4.3 * inch, f"Completed: {completed_str}    |    Expires: {expires_str}")

    c.setFont("Helvetica", 12)
    c.drawString(margin + 0.2 * inch, margin + 0.35 * inch, f"Certificate ID: {cycle.certificate_id}")

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="certificate-{cycle.certificate_id}.pdf"'
    return resp
