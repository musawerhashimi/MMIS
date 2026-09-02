"""
Production settings — targets an on-premise university server.

Assumes the app sits behind nginx which terminates TLS. If the university
runs it on plain HTTP inside the campus network, set SECURE_SSL_REDIRECT=False
in the environment.
"""
from .base import *  # noqa: F403

DEBUG = False

# Fail loudly at boot rather than silently running with the dev key.
SECRET_KEY = config("SECRET_KEY")  # noqa: F405

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())  # noqa: F405

CELERY_TASK_ALWAYS_EAGER = False
