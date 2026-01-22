from django.conf import settings

def frontend_url(request):
    return {
        "FRONTEND_URL": getattr(settings, "FRONTEND_URL", "").rstrip("/"),
        "APP_PATH": getattr(settings, "APP_PATH", "/app/"),
    }
