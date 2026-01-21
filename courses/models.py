from django.conf import settings
from django.db import models
from dateutil.relativedelta import relativedelta
from django.utils.timezone import now
import uuid
from django.contrib.auth import get_user_model

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

    # Cache-bust tokens (helps prevent stale/corrupt cached partial video ranges)
    video_cache_bust = models.CharField(max_length=16, blank=True, default="")
    pdf_cache_bust = models.CharField(max_length=16, blank=True, default="")

    # This lets you 'retire' older versions without deleting history.
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)

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

    @property
    def video_url(self):
        """
        Use this in templates instead of video_file.url:
        <source src="{{ course_version.video_url }}" type="video/mp4" />
        """
        if not self.video_file:
            return ""
        url = self.video_file.url
        if self.video_cache_bust:
            joiner = "&" if "?" in url else "?"
            url = f"{url}{joiner}v={self.video_cache_bust}"
        return url

    @property
    def pdf_url(self):
        if not self.pdf_file:
            return ""
        url = self.pdf_file.url
        if self.pdf_cache_bust:
            joiner = "&" if "?" in url else "?"
            url = f"{url}{joiner}v={self.pdf_cache_bust}"
        return url

    def save(self, *args, **kwargs):
        # Detect file changes so we only bump the token when the file changes
        old = None
        if self.pk:
            old = CourseVersion.objects.filter(pk=self.pk).values(
                "video_file", "pdf_file", "video_cache_bust", "pdf_cache_bust"
            ).first()

        # If new record, or video changed, bump token
        if not self.pk or (old and old["video_file"] != (self.video_file.name if self.video_file else "")):
            if self.video_file:
                self.video_cache_bust = uuid.uuid4().hex[:10]

        # If new record, or pdf changed, bump token
        if not self.pk or (old and old["pdf_file"] != (self.pdf_file.name if self.pdf_file else "")):
            if self.pdf_file:
                self.pdf_cache_bust = uuid.uuid4().hex[:10]

        super().save(*args, **kwargs)


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
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="cycles"
    )

    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    score = models.PositiveSmallIntegerField(null=True, blank=True)
    passed = models.BooleanField(default=False)

    certificate_id = models.CharField(max_length=32, unique=True, editable=False)

    reminder_30_sent_at = models.DateTimeField(null=True, blank=True)
    reminder_7_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-completed_at"]
        permissions = [
            ("can_audit_certs", "Can search and download certificates for all users"),
        ]

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if is_new and not self.certificate_id:
            self.certificate_id = uuid.uuid4().hex[:10]

        # Only set expires_at when a completion exists
        if self.completed_at and not self.expires_at:
            self.expires_at = self.completed_at + relativedelta(months=11)

        super().save(*args, **kwargs)

    @property
    def days_remaining(self):
        if not self.expires_at:
            return None
        return (self.expires_at.date() - now().date()).days

    def __str__(self):
        d = self.completed_at.date() if self.completed_at else "—"
        return f"{self.assignment} completed {d}"


User = get_user_model()

class AssignmentRule(models.Model):
    FREQUENCY_CHOICES = [
        ("ANNUAL", "Annual"),
        ("SEMIANNUAL", "Semiannual"),
        ("QUARTERLY", "Quarterly"),
        ("MONTHLY", "Monthly"),
    ]

    name = models.CharField(max_length=200)
    course_version = models.ForeignKey("courses.CourseVersion", on_delete=models.CASCADE)

    # who gets assigned (start simple: everyone; later: groups/departments)
    assign_to_all_users = models.BooleanField(default=True)

    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default="ANNUAL")

    # expiration window & reminder behavior
    cycle_days = models.PositiveIntegerField(default=365)     # expires_at = assigned_at + cycle_days
    remind_days_before = models.PositiveIntegerField(default=30)

    is_active = models.BooleanField(default=True)

    # tracking so we don’t create duplicates
    last_run_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

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