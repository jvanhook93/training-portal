import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Create/reset a superuser from env vars (non-interactive)."

    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME", "").strip()
        password = os.getenv("ADMIN_PASSWORD", "").strip()
        email = os.getenv("ADMIN_EMAIL", "").strip()

        if not username or not password:
            self.stdout.write("bootstrap_admin: missing ADMIN_USERNAME/ADMIN_PASSWORD; skipping.")
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})

        # Always enforce superuser + reset password (so it can't be 'wrong')
        user.is_staff = True
        user.is_superuser = True
        if email:
            user.email = email
        user.set_password(password)
        user.save()

        self.stdout.write(f"bootstrap_admin: {'created' if created else 'updated'} superuser '{username}'.")
        self.stdout.write("bootstrap_admin: running...")
        self.stdout.write(f"bootstrap_admin: updated superuser '{username}'.")