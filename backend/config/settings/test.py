"""Settings used by the test suite."""
from .base import *  # noqa: F403

DEBUG = False

# Long enough for HS256 to stop warning; this key never leaves the tests.
SECRET_KEY = "test-only-key-not-used-anywhere-outside-the-test-suite"

# Whitenoise complains about a missing staticfiles directory during tests,
# and static files are irrelevant to what these tests check.
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]  # noqa: F405

# Fast, throwaway database. Override POSTGRES_DB in CI if you want to test
# against real Postgres behaviour (JSON fields, constraints).
DATABASES["default"] = {  # noqa: F405
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CELERY_TASK_ALWAYS_EAGER = True

STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
}
