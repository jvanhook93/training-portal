import os
from django.contrib.auth import get_user_model

def bootstrap_admin():
    username = os.getenv("admin")
    email = os.getenv("jvanhook@integranethealth.com")
    password = os.getenv("1913North!")

    if not (username and password):
        return

    User = get_user_model()
    if User.objects.filter(username=username).exists():
        return

    User.objects.create_superuser(username=username, email=email or "", password=password)
