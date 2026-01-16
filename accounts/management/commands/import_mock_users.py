import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction


User = get_user_model()


def to_bool(v):
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ("1", "true", "t", "yes", "y")


class Command(BaseCommand):
    help = "Import mock users from a Mockaroo CSV."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to CSV file")
        parser.add_argument("--default-password", type=str, default="Password123!",
                           help="Default password if CSV doesn't include one")
        parser.add_argument("--update-existing", action="store_true",
                           help="Update existing users if username/email matches")

    @transaction.atomic
    def handle(self, *args, **opts):
        csv_path = Path(opts["csv_path"]).expanduser().resolve()
        default_password = opts["default_password"]
        update_existing = opts["update_existing"]

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"CSV not found: {csv_path}"))
            return

        created = 0
        updated = 0
        skipped = 0

        with csv_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required = {"username", "email"}
            missing = required - set([h.strip() for h in reader.fieldnames or []])
            if missing:
                self.stderr.write(self.style.ERROR(f"CSV missing required columns: {', '.join(sorted(missing))}"))
                return

            for row in reader:
                username = (row.get("username") or "").strip()
                email = (row.get("email") or "").strip().lower()
                first_name = (row.get("first_name") or "").strip()
                last_name = (row.get("last_name") or "").strip()

                if not username or not email:
                    skipped += 1
                    continue

                is_staff = to_bool(row.get("is_staff"))
                is_superuser = to_bool(row.get("is_superuser"))
                pw = (row.get("password") or "").strip() or default_password

                # find existing
                user = None
                if update_existing:
                    user = User.objects.filter(username=username).first() or User.objects.filter(email=email).first()

                if user:
                    user.email = email
                    user.first_name = first_name
                    user.last_name = last_name
                    user.is_staff = is_staff
                    user.is_superuser = is_superuser
                    user.set_password(pw)
                    user.save()
                    updated += 1
                else:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        password=pw,
                    )
                    user.is_staff = is_staff
                    user.is_superuser = is_superuser
                    user.save()
                    created += 1

        self.stdout.write(self.style.SUCCESS(f"Done. created={created} updated={updated} skipped={skipped}"))
