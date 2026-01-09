from django.conf import settings
from django.db import models
from courses.models import CourseVersion


class Quiz(models.Model):
    """
    One quiz per CourseVersion (typical for compliance training).
    """
    course_version = models.OneToOneField(CourseVersion, on_delete=models.CASCADE, related_name="quiz")
    title = models.CharField(max_length=255, default="Course Quiz")

    def __str__(self) -> str:
        return f"Quiz for {self.course_version}"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    order = models.PositiveIntegerField(default=1)

    def __str__(self) -> str:
        return f"Q{self.order}: {self.prompt[:60]}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=512)
    is_correct = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.text


class Attempt(models.Model):
    """
    A user taking a quiz. This is where traceability starts.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT, related_name="attempts")

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    score = models.PositiveSmallIntegerField(null=True, blank=True)
    passed = models.BooleanField(default=False)

    # Traceability fields (basic)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.user} attempt on {self.quiz}"


class AnswerAttempt(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    choice = models.ForeignKey(Choice, on_delete=models.PROTECT, null=True, blank=True)
    is_correct = models.BooleanField(default=False)

    class Meta:
        unique_together = ("attempt", "question")
