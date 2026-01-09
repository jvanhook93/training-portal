from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """
    Append-only audit log. Do NOT edit rows; only add.
    """
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="audit_events"
    )

    action = models.CharField(max_length=100)  # e.g. COURSE_CREATED, ASSIGNED, QUIZ_SUBMITTED
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)

    # Store a JSON-like string now; later can convert to JSONField if desired
    details = models.TextField(blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["action"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.created_at} {self.action} by {self.actor}"
