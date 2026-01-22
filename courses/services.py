# courses/services.py
from django.db import transaction
from django.utils import timezone
from courses.models import Course, CourseVersion, Assignment

COMPANY_DOMAIN = "integranethealth.com"

def is_company_user(email: str) -> bool:
    if not email or "@" not in email:
        return False
    return email.split("@", 1)[1].lower() == COMPANY_DOMAIN

@transaction.atomic
def assign_required_company_courses(user):
    """
    Assign required courses to a user (only if not already assigned).
    Uses latest published CourseVersion.
    """
    required_courses = Course.objects.filter(is_active=True, required_for_company=True)

    for course in required_courses:
        cv = (
            CourseVersion.objects
            .filter(course=course, is_published=True)
            .order_by("-published_at", "-id")
            .first()
        )
        if not cv:
            continue

        # avoid duplicates: only one active assignment per user+course_version
        Assignment.objects.get_or_create(
            assignee=user,
            course_version=cv,
            defaults={
                "assigned_at": timezone.now(),
                "status": Assignment.Status.ASSIGNED,
            }
        )
