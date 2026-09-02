"""Local development settings."""
from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# SQLite by default so a developer can clone and run with nothing installed.
# Set USE_POSTGRES=True (and the POSTGRES_* vars) to match production locally.
if not config("USE_POSTGRES", default=False, cast=bool):  # noqa: F405
    DATABASES["default"] = {  # noqa: F405
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }

# In-memory channel layer avoids needing Redis just to open the app.
if not config("USE_REDIS", default=False, cast=bool):  # noqa: F405
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Let any localhost port through while developing.
CORS_ALLOW_ALL_ORIGINS = True

# Plain static storage in dev — no manifest hashing, so missing files
# don't blow up the dev server.
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
}

# Email lands in the console instead of a real SMTP server.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Run Celery tasks inline so a developer doesn't need a worker running.
CELERY_TASK_ALWAYS_EAGER = config("CELERY_EAGER", default=True, cast=bool)  # noqa: F405
