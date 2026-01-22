# config/settings.py
from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import os

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


def _csv_env(name: str):
    """Read comma-separated env var into a clean list (no blanks)."""
    return [v.strip() for v in os.getenv(name, "").split(",") if v.strip()]


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default) in ("1", "true", "True", "yes", "YES", "on", "ON")


# -----------------------------------------------------------------------------
# Core security / environment
# -----------------------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-change-me")

# Use DJANGO_DEBUG=1 locally (and temporarily on Railway when debugging)
DEBUG = _env_bool("DJANGO_DEBUG", "1")

# Hosts
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,.up.railway.app"
    ).split(",")
    if h.strip()
]

# Optional extra hosts (custom domains etc.)
for h in _csv_env("EXTRA_ALLOWED_HOSTS"):
    if h not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(h)

# Railway / proxies
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

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
    # CORS MUST be first (before CommonMiddleware)
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
                # Do NOT add apps.core.context_processors.frontend_url unless it exists.
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

WHITENOISE_USE_FINDERS = True

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# WhiteNoise
# - In DEBUG we allow finder-based serving (no collectstatic needed)
# - In prod we use hashed manifest files
if DEBUG:
    WHITENOISE_USE_FINDERS = True
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
    # If you ever deploy with missing hashed files, this prevents hard-crash
    WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(BASE_DIR / "media")))

# -----------------------------------------------------------------------------
# CORS / CSRF
# -----------------------------------------------------------------------------
# Railway vars you should set:
# CORS_ALLOWED_ORIGINS=https://training-portal-8pr.pages.dev
# CSRF_TRUSTED_ORIGINS=https://training-portal-8pr.pages.dev,https://web-production-4c59f.up.railway.app
CORS_ALLOWED_ORIGINS = _csv_env("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = _csv_env("CSRF_TRUSTED_ORIGINS")

# Local dev convenience
if DEBUG:
    for o in ["http://localhost:5173", "http://127.0.0.1:5173"]:
        if o not in CORS_ALLOWED_ORIGINS:
            CORS_ALLOWED_ORIGINS.append(o)

    for o in ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"]:
        if o not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(o)

# OPTIONAL but very useful: allow all Pages.dev preview subdomains
# (won't override the explicit list above; it's an additional allow mechanism)
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https:\/\/.*\.pages\.dev$",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "origin",
    "x-csrftoken",
    "x-requested-with",
]

# Cookies / SameSite
# If frontend and backend are on different domains in prod, you need SameSite=None; Secure=True
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
