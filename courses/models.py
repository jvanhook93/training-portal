from django.conf import settings
from django.db import models
from dateutil.relativedelta import relativedelta
from django.utils.timezone import now
import uuid

class Course(models.Model):
    """
    A logical training course (e.g., HIPAA, MOC).
    """
    code = models.CharField(max_length=50, unique=True)  # e.g. HIPAA, MOC
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="courses_created"
    )

    def __str__(self) -> str:
        return f"{self.code} - {self.title}"


class CourseVersion(models.Model):
    """
    Immutable published version of a course.
    Each completion must tie to a specific CourseVersion.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=40)  # e.g. "2026.01", "v3"
    changelog = models.TextField(blank=True)

    video_file = models.FileField(upload_to="training_videos/", null=True, blank=True)
    pdf_file = models.FileField(upload_to="training_pdfs/", null=True, blank=True)

    # This lets you 'retire' older versions without deleting history.
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)

    # Optional: what score is required to pass
    pass_score = models.PositiveSmallIntegerField(default=80)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="course_versions_created"
    )

    class Meta:
        unique_together = ("course", "version")

    def __str__(self) -> str:
        return f"{self.course.code} {self.version}"


class VideoProgress(models.Model):
    """
    Track how much of a CourseVersion's video a user has watched.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="video_progress")
    course_version = models.ForeignKey(CourseVersion, on_delete=models.PROTECT, related_name="video_progress")

    watched_seconds = models.PositiveIntegerField(default=0)
    total_seconds = models.PositiveIntegerField(default=0)
    percent = models.PositiveSmallIntegerField(default=0)  # 0-100

    started_at = models.DateTimeField(null=True, blank=True)
    last_ping_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "course_version")


class Assignment(models.Model):
    """
    Assign a specific CourseVersion to a user with due dates.
    """
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assignments")
    course_version = models.ForeignKey(CourseVersion, on_delete=models.PROTECT, related_name="assignments")

    assigned_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField(null=True, blank=True)

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assignments_made"
    )

    class Status(models.TextChoices):
        ASSIGNED = "ASSIGNED"
        IN_PROGRESS = "IN_PROGRESS"
        COMPLETED = "COMPLETED"
        OVERDUE = "OVERDUE"

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)

    def __str__(self) -> str:
        return f"{self.assignee} -> {self.course_version}"


class AssignmentCycle(models.Model):
    """
    One completed compliance cycle for an assignment.
    This preserves history for audits and drives expiration logic.
    """
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="cycles"
    )

    completed_at = models.DateTimeField(default=now)
    expires_at = models.DateTimeField()

    score = models.PositiveSmallIntegerField(null=True, blank=True)
    passed = models.BooleanField(default=True)

    certificate_id = models.CharField(max_length=32, unique=True, editable=False)

    class Meta:
        ordering = ["-completed_at"]
        permissions = [
        ("can_audit_certs", "Can search and download certificates for all users"),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            # Auto-generate cert id
            self.certificate_id = uuid.uuid4().hex[:10]

            # Default 11-month expiration unless overridden later
            self.expires_at = self.completed_at + relativedelta(months=11)

        super().save(*args, **kwargs)

    @property
    def days_remaining(self):
        return (self.expires_at.date() - now().date()).days

    def __str__(self):
        return f"{self.assignment} completed {self.completed_at.date()}"


class Quiz(models.Model):
    course_version = models.OneToOneField(
        "CourseVersion",
        on_delete=models.CASCADE,
        related_name="course_quiz",
    )
    is_required = models.BooleanField(default=False)

    def __str__(self):
        return f"Quiz for {self.course_version}"


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()

    order = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return f"Q{self.order}: {self.prompt[:40]}"


class QuizChoice(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text