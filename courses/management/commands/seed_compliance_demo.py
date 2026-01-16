import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from courses.models import Course, CourseVersion, Assignment, AssignmentCycle


User = get_user_model()


class Command(BaseCommand):
    help = "Seed a demo course + assignments/cycles with compliant/due soon/expired/not-started distributions."

    def add_arguments(self, parser):
        # NOTE: argparse reserves --version; use --course-version instead
        parser.add_argument("--code", type=str, default="DEMO-101", help="Course code")
        parser.add_argument("--title", type=str, default="Demo Compliance Course", help="Course title")
        parser.add_argument("--course-version", dest="course_version", type=str, default="1.0",
                            help="CourseVersion.version string (e.g. 1.0, 2026.01)")

        parser.add_argument("--users", type=int, default=0,
                            help="Limit number of users seeded (0 = all active users)")
        parser.add_argument("--reset", action="store_true",
                            help="Delete existing assignments for this course version before seeding")

        # distribution (percentages must add to 100)
        parser.add_argument("--pct-compliant", type=int, default=40)
        parser.add_argument("--pct-duesoon", type=int, default=30)
        parser.add_argument("--pct-expired", type=int, default=20)
        parser.add_argument("--pct-notstarted", type=int, default=10)

        parser.add_argument("--seed", type=int, default=1337, help="Random seed for repeatable demo")
        parser.add_argument("--assigned-by", type=str, default="",
                            help="Username of assigning user (optional)")

    @transaction.atomic
    def handle(self, *args, **opts):
        seed = opts["seed"]
        random.seed(seed)

        pct_compliant = opts["pct_compliant"]
        pct_duesoon = opts["pct_duesoon"]
        pct_expired = opts["pct_expired"]
        pct_notstarted = opts["pct_notstarted"]

        if pct_compliant + pct_duesoon + pct_expired + pct_notstarted != 100:
            raise SystemExit("Percentages must add to 100.")

        now = timezone.now()

        # course + published version
        course, _ = Course.objects.get_or_create(
            code=opts["code"],
            defaults={"title": opts["title"], "description": "Seeded demo course for audit/compliance previews."},
        )
        if course.title != opts["title"]:
            course.title = opts["title"]
            course.save(update_fields=["title"])

        cv, _ = CourseVersion.objects.get_or_create(
            course=course,
            version=opts["course_version"],
            defaults={"is_published": True, "published_at": now, "pass_score": 80},
        )
        if not cv.is_published:
            cv.is_published = True
            cv.published_at = cv.published_at or now
            cv.save(update_fields=["is_published", "published_at"])

        assigned_by = None
        if opts["assigned_by"]:
            assigned_by = User.objects.filter(username=opts["assigned_by"]).first()

        users_qs = User.objects.filter(is_active=True).order_by("id")
        if opts["users"] and opts["users"] > 0:
            users_qs = users_qs[: opts["users"]]
        users = list(users_qs)

        if not users:
            self.stdout.write(self.style.WARNING("No users found to seed."))
            return

        if opts["reset"]:
            Assignment.objects.filter(course_version=cv, assignee__in=users).delete()

        buckets = (
            ["COMPLIANT"] * pct_compliant
            + ["DUE_SOON"] * pct_duesoon
            + ["EXPIRED"] * pct_expired
            + ["NOT_STARTED"] * pct_notstarted
        )
        # Shuffle per-user assignment status
        random.shuffle(buckets)

        created_assignments = 0
        created_cycles = 0

        for i, u in enumerate(users):
            label = buckets[i % len(buckets)]

            # create assignment
            a = Assignment.objects.create(
                assignee=u,
                course_version=cv,
                assigned_by=assigned_by,
                # due_at: for display; use something sensible
                due_at=now + timedelta(days=14),
                status=Assignment.Status.ASSIGNED,
            )
            created_assignments += 1

            if label == "NOT_STARTED":
                # cycle exists but not completed: shows "Assigned" / not started
                AssignmentCycle.objects.create(
                    assignment=a,
                    completed_at=None,
                    expires_at=None,
                    score=None,
                    passed=False,
                )
                a.status = Assignment.Status.ASSIGNED
                a.save(update_fields=["status"])
                created_cycles += 1
                continue

            # completed cycle
            completed_at = now - timedelta(days=random.randint(1, 120))

            if label == "COMPLIANT":
                expires_at = now + timedelta(days=random.randint(60, 180))
                a.status = Assignment.Status.COMPLETED
            elif label == "DUE_SOON":
                expires_at = now + timedelta(days=random.randint(1, 30))
                a.status = Assignment.Status.COMPLETED
            else:  # EXPIRED
                expires_at = now - timedelta(days=random.randint(1, 180))
                a.status = Assignment.Status.OVERDUE

            AssignmentCycle.objects.create(
                assignment=a,
                completed_at=completed_at,
                expires_at=expires_at,
                score=random.randint(80, 100),
                passed=True,
            )
            a.save(update_fields=["status"])
            created_cycles += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(users)} users for {course.code} v{cv.version}. "
            f"assignments={created_assignments} cycles={created_cycles} seed={seed}"
        ))
        self.stdout.write(self.style.SUCCESS(
            "Buckets: COMPLIANT/DUE_SOON/EXPIRED/NOT_STARTED = "
            f"{pct_compliant}/{pct_duesoon}/{pct_expired}/{pct_notstarted}"
        ))
