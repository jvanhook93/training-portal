import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Create/update an initial superuser from env vars (non-interactive)."

    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME", "").strip()
        email = os.getenv("ADMIN_EMAIL", "").strip()
        password = os.getenv("ADMIN_PASSWORD", "").strip()

        if not username or not password:
            self.stdout.write("bootstrap_admin: ADMIN_USERNAME/ADMIN_PASSWORD not set; skipping.")
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        if created:
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
            self.stdout.write(f"bootstrap_admin: created superuser '{username}'.")
        else:
            # ensure permissions and optionally update password
            changed = False
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if not user.is_superuser:
                user.is_superuser = True
                changed = True
            if password:
                user.set_password(password)
                changed = True
            if email and user.email != email:
                user.email = email
                changed = True
            if changed:
                user.save()
            self.stdout.write(f"bootstrap_admin: ensured superuser '{username}'.")
