from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import os

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# Core security / environment
# -----------------------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-change-me")

# Use DJANGO_DEBUG=1 on local and (temporarily) on Railway if debugging
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"

# Hosts
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,.up.railway.app"
    ).split(",")
    if h.strip()
]

# Add your custom domain if you use it (safe to include even if not live yet)
# Example: training.integranethealth.com
extra_hosts = os.getenv("EXTRA_ALLOWED_HOSTS", "")
if extra_hosts:
    for h in extra_hosts.split(","):
        h = h.strip()
        if h and h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(h)

# If behind a proxy (Railway), this makes request.is_secure() work correctly
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Frontend URL used for redirects (Cloudflare Pages in prod, Vite in dev)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
APP_PATH = os.getenv("APP_PATH", "/app/")

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = os.getenv("LOGIN_REDIRECT_URL", f"{FRONTEND_URL}/")
LOGOUT_REDIRECT_URL = os.getenv("LOGOUT_REDIRECT_URL", f"{FRONTEND_URL}/")

# -----------------------------------------------------------------------------
# Email (safe default for dev)
# -----------------------------------------------------------------------------
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "training@integranethealth.com")

# -----------------------------------------------------------------------------
# Application definition
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "corsheaders",

    "accounts",
    "courses",
    "audits",
    "apps.core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",

    # WhiteNoise must be right after SecurityMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",

                # IMPORTANT:
                # If you don't have apps/core/context_processors.py with frontend_url(),
                # this WILL crash admin with a 500. Keep it removed unless it's real.
                # "apps.core.context_processors.frontend_url",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL:
    import dj_database_url

    # Railway Postgres: ssl_require should be True
    # Local: you won't usually have DATABASE_URL set
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# -----------------------------------------------------------------------------
# Password validation
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Static + Media
# -----------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Your built React output lives in BASE_DIR/static/app/*
STATICFILES_DIRS = []
_static_dir = BASE_DIR / "static"
if _static_dir.exists():
    STATICFILES_DIRS.append(_static_dir)

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# WhiteNoise behavior
if DEBUG:
    WHITENOISE_USE_FINDERS = True
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(BASE_DIR / "media")))

# -----------------------------------------------------------------------------
# CORS / CSRF
# -----------------------------------------------------------------------------
# Recommended Railway vars:
# CORS_ALLOWED_ORIGINS=https://training-portal-8pr.pages.dev
# CSRF_TRUSTED_ORIGINS=https://training-portal-8pr.pages.dev,https://web-production-4c59f.up.railway.app
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]

# Local dev convenience: allow Vite dev server
if DEBUG:
    if "http://localhost:5173" not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append("http://localhost:5173")
    if "http://127.0.0.1:5173" not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append("http://127.0.0.1:5173")

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# Local dev trusted origins convenience
if DEBUG:
    for o in ["http://localhost:5173", "http://127.0.0.1:5173", "http://127.0.0.1:8000", "http://localhost:8000"]:
        if o not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(o)

# Cookies / SameSite
if DEBUG:
    CSRF_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
else:
    CSRF_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

# -----------------------------------------------------------------------------
# Security defaults (safe)
# -----------------------------------------------------------------------------
X_FRAME_OPTIONS = "DENY"

# -----------------------------------------------------------------------------
# Default primary key
# -----------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
