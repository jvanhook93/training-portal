import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from courses.models import Course, CourseVersion, Assignment, AssignmentCycle

User = get_user_model()


class Command(BaseCommand):
    help = "Seed a demo Course + assign to users with cycles showing compliant/due soon/expired."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=0, help="Limit users (0 = all)")
        parser.add_argument("--code", type=str, default="DEMO-101", help="Course code")
        parser.add_argument("--title", type=str, default="Demo Compliance Course", help="Course title")
        parser.add_argument("--course-version", type=str, default="1.0", help="Published course version string")
        parser.add_argument("--pass-score", type=int, default=80, help="Pass score percent")
        parser.add_argument("--admin-username", type=str, default="", help="Who 'assigned_by' should be (username).")
        parser.add_argument("--update-existing", action="store_true", help="Update existing assignments/cycles")
        parser.add_argument("--dry-run", action="store_true", help="Do not write changes")

    @transaction.atomic
    def handle(self, *args, **opts):
        now = timezone.now()
        dry = opts["dry_run"]
        limit = opts["users"]
        update_existing = opts["update_existing"]

        # Pick an assigner (assigned_by). If not provided, try first superuser, else None.
        assigner = None
        if opts["admin_username"]:
            assigner = User.objects.filter(username=opts["admin_username"]).first()
        if not assigner:
            assigner = User.objects.filter(is_superuser=True).order_by("id").first()

        # --- Create course + version ---
        course, _ = Course.objects.get_or_create(
            code=opts["code"],
            defaults={
                "title": opts["title"],
                "description": "Seeded demo course for audits/compliance walkthroughs.",
            },
        )

        # Keep display nice
        course.title = opts["title"]
        if hasattr(course, "description") and not course.description:
            course.description = "Seeded demo course for audits/compliance walkthroughs."
        if not dry:
            course.save()

        cv, _ = CourseVersion.objects.get_or_create(
            course=course,
            version=opts["course_version"],
            defaults={"pass_score": opts["pass_score"]},
        )
        if hasattr(cv, "pass_score"):
            cv.pass_score = opts["pass_score"]
        if hasattr(cv, "is_published"):
            cv.is_published = True
        if not dry:
            cv.save()

        if hasattr(course, "published_version"):
            course.published_version = cv
            if not dry:
                course.save(update_fields=["published_version"])

        # --- Users to seed ---
        qs = User.objects.all().order_by("id")
        if limit and limit > 0:
            qs = qs[:limit]
        users = list(qs)

        if not users:
            self.stdout.write(self.style.WARNING("No users found."))
            return

        # Buckets that match your dashboard logic:
        # EXPIRED: expires_at < today
        # DUE SOON: expires_at <= 30 days
        # COMPLIANT: expires_at > 30 days
        def pick_bucket():
            r = random.random()
            if r < 0.60:
                return "COMPLIANT"
            if r < 0.85:
                return "DUE_SOON"
            return "EXPIRED"

        created_a = updated_a = created_c = updated_c = 0

        for u in users:
            # One assignment per user per course version
            a = Assignment.objects.filter(assignee=u, course_version=cv).first()

            if a and not update_existing:
                continue

            assigned_at = now - timedelta(days=random.randint(0, 14))
            bucket = pick_bucket()

            if bucket == "COMPLIANT":
                due_at = now + timedelta(days=random.randint(45, 180))
                expires_at = now + timedelta(days=random.randint(45, 180))
                status = "COMPLETED"
                passed = True
                score = random.randint(opts["pass_score"], 100)
            elif bucket == "DUE_SOON":
                due_at = now + timedelta(days=random.randint(1, 30))
                expires_at = now + timedelta(days=random.randint(1, 30))
                status = "COMPLETED"
                passed = True
                score = random.randint(opts["pass_score"], 100)
            else:  # EXPIRED
                due_at = now - timedelta(days=random.randint(1, 30))
                expires_at = now - timedelta(days=random.randint(1, 60))
                # You may want these to be OVERDUE, depending on what your UI expects.
                # Your dashboard code overrides label based on expires_at anyway.
                status = "OVERDUE"
                passed = random.random() < 0.80
                score = random.randint(40, 100) if passed else random.randint(0, opts["pass_score"] - 1)

            completed_at = assigned_at + timedelta(days=random.randint(0, 10))

            # --- upsert assignment ---
            if not a:
                a = Assignment(
                    assignee=u,
                    course_version=cv,
                    assigned_by=assigner,
                    assigned_at=assigned_at,
                    due_at=due_at,
                    status=status,
                )
                if not dry:
                    a.save()
                created_a += 1
            else:
                a.assigned_by = assigner
                a.assigned_at = assigned_at
                a.due_at = due_at
                a.status = status
                if not dry:
                    a.save()
                updated_a += 1

            # --- upsert cycle ---
            # Your dashboard uses a.cycles.first() and you said ordering is set to newest,
            # but to be safe we replace the most recent cycle when updating.
            existing_cycle = a.cycles.order_by("-completed_at").first()
            if existing_cycle and update_existing:
                existing_cycle.completed_at = completed_at
                existing_cycle.expires_at = expires_at
                existing_cycle.score = score
                existing_cycle.passed = passed
                existing_cycle.certificate_id = existing_cycle.certificate_id or f"DEMO-{a.id}-{u.id}"
                if not dry:
                    existing_cycle.save()
                updated_c += 1
            else:
                c = AssignmentCycle(
                    assignment=a,
                    completed_at=completed_at,
                    expires_at=expires_at,
                    score=score,
                    passed=passed,
                    certificate_id=f"DEMO-{a.id}-{u.id}",
                )
                if not dry:
                    c.save()
                created_c += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. assignments created={created_a} updated={updated_a} cycles created={created_c} updated={updated_c} users={len(users)}"
        ))
