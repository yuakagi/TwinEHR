"""
Django settings.
"""

import os
from pathlib import Path

# Django Settings
# region Django Settings
# ===========
# Key configs
# ===========
SITE_ID = 1
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key")
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "false") == "true"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost").split(",")

# =================
# Database setups
# =================
DATABASES = {
    # Django's default database
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("PG_DB"),
        "USER": os.environ.get("PG_USER"),
        "PASSWORD": os.environ.get("PG_PASSWORD"),
        "HOST": "django_db",
        "PORT": 5432,
        "CONN_MAX_AGE": int(os.environ.get("PG_CONN_MAX_AGE", 60)),
        "CONN_HEALTH_CHECKS": True,
    },
    # Another database for clinical records
    # NOTE: this is made read-only by `-c default_transaction_read_only=on`
    "clinical_records": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("CR_DB"),
        "USER": os.environ.get("CR_USER"),
        "PASSWORD": os.environ.get("CR_PASSWORD"),
        "HOST": os.environ.get("CR_HOST"),
        "PORT": os.environ.get("CR_PORT"),
        "CONN_MAX_AGE": int(os.environ.get("CR_CONN_MAX_AGE", 60)),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "options": f"-c search_path={os.environ.get('CR_SCHEMA', 'public')} -c default_transaction_read_only=on"
        },
    },
}
DATABASE_ROUTERS = ["clinical_records.db_router.ClinicalRecordsRouter"]

# ================
# Apps & Middleware
# =================
# Application definition
INSTALLED_APPS = [
    # Default apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # 3rd packages and related.
    "axes",  # django-axes for rate limiting
    # Created apps
    "general.apps.GeneralConfig",
    "accounts.apps.AccountsConfig",  # Consider change name -> account
    "staff.apps.StaffConfig",
    "clinical_records.apps.ClinicalRecordsConfig",  # Consider change name -> patient
    "simulator.apps.SimulatorConfig",
]
MIDDLEWARE = [
    # Default.
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # 3rd packages.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "axes.middleware.AxesMiddleware",
]
WSGI_APPLICATION = "Twin.wsgi.application"
# Enable WhiteNoise compression and caching in production
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# ================
# Directory & URLs
# ================
# Dirs
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
# Url
ROOT_URLCONF = "Twin.urls"
LOGOUT_REDIRECT_URL = "landing"
MEDIA_URL = "/media/"
STATIC_URL = "/static/"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ==============
# Authentication
# ==============
AUTH_USER_MODEL = "accounts.CustomUser"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
]
# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
# Axes settings
AXES_FAILURE_LIMIT = 10  # Number of failed login attempts before lockout
AXES_COOLOFF_TIME = 0  # Lockout time in hours (set to None for permanent)
AXES_RESET_ON_SUCCESS = True  # Reset count after successful login


# ====================
# Internationalization
# ====================
# https://docs.djangoproject.com/en/4.2/topics/i18n/
TIME_ZONE = "Asia/Tokyo"
LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_TZ = True  # Default is True.

# =============
# Model sttings
# =============
# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =================
# Networks security
# =================
# HTTPS-related settings disabled
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_PROXY_SSL_HEADER = None
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
# Still recommended for security regardless of HTTPS
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
# Others
X_FRAME_OPTIONS = "DENY"  # <- for click jacking

# endregion
