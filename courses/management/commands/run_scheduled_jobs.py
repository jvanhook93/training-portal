from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.db import transaction

from courses.models import Assignment, AssignmentCycle, AssignmentRule


User = get_user_model()


class Command(BaseCommand):
    help = "Runs scheduled jobs: reminder emails + recurring assignments."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Print actions but do not write/send.")
        parser.add_argument("--remind-days", type=int, default=30, help="Send reminders this many days before expiry.")
        parser.add_argument("--only-completed", action="store_true",
                            help="Only remind on cycles that have completed_at set (recommended).")

    @transaction.atomic
    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        remind_days = opts["remind_days"]
        only_completed = opts["only_completed"]
        now = timezone.now()

        # -------------------------
        # 1) Reminder emails
        # -------------------------
        soon_end = now + timedelta(days=remind_days)

        cycles_qs = (
            AssignmentCycle.objects
            .select_related("assignment", "assignment__assignee", "assignment__course_version", "assignment__course_version__course")
            .filter(
                expires_at__isnull=False,
                expires_at__gt=now,
                expires_at__lte=soon_end,
                reminder_30_sent_at__isnull=True,
            )
        )

        if only_completed:
            cycles_qs = cycles_qs.filter(completed_at__isnull=False)

        sent = 0
        for c in cycles_qs:
            u = c.assignment.assignee
            if not u.email:
                continue

            course = c.assignment.course_version.course
            course_title = f"{course.code} - {course.title}"
            days_left = (c.expires_at.date() - now.date()).days

            subject = f"Training expiring soon: {course_title}"
            body = (
                f"Hi {u.first_name or u.username},\n\n"
                f"Your training '{course_title}' will expire in {days_left} day(s) on {c.expires_at.date()}.\n"
                f"Please log in and complete the renewal if required.\n\n"
                f"{settings.DEFAULT_FROM_EMAIL}\n"
            )

            if dry:
                self.stdout.write(f"[DRY] Would email {u.email}: {course_title} expires {c.expires_at}")
            else:
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [u.email], fail_silently=False)
                c.reminder_30_sent_at = now
                c.save(update_fields=["reminder_30_sent_at"])
                sent += 1

        self.stdout.write(self.style.SUCCESS(f"Reminder emails sent: {sent}"))

        # -------------------------
        # 2) Recurring assignments
        # -------------------------
        rules = AssignmentRule.objects.select_related("course_version", "course_version__course").filter(is_active=True)

        created_assignments = 0
        created_cycles = 0

        for rule in rules:
            if not rule.assign_to_all_users:
                continue

            users = User.objects.filter(is_active=True)

            for u in users:
                latest_assignment = (
                    Assignment.objects
                    .filter(assignee=u, course_version=rule.course_version)
                    .order_by("-assigned_at", "-id")
                    .first()
                )

                need_new = False
                if not latest_assignment:
                    need_new = True
                else:
                    latest_cycle = latest_assignment.cycles.order_by("-expires_at", "-id").first()
                    if not latest_cycle:
                        need_new = True
                    elif latest_cycle.expires_at and latest_cycle.expires_at <= now:
                        need_new = True

                if not need_new:
                    continue

                if dry:
                    self.stdout.write(f"[DRY] Would create assignment for {u.username} -> {rule.course_version}")
                    continue

                # Create a new assignment
                a = Assignment.objects.create(
                    assignee=u,
                    course_version=rule.course_version,
                    due_at=now + timedelta(days=rule.cycle_days),
                    assigned_by=None,
                    status=Assignment.Status.ASSIGNED,
                )
                created_assignments += 1

                # Create the cycle but NOT completed
                AssignmentCycle.objects.create(
                    assignment=a,
                    completed_at=None,
                    expires_at=None,
                    passed=False,
                )
                created_cycles += 1

            rule.last_run_at = now
            rule.save(update_fields=["last_run_at"])

        self.stdout.write(self.style.SUCCESS(
            f"Recurring: created assignments={created_assignments}, cycles={created_cycles}"
        ))
