from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

SECRET_KEY = env("SECRET_KEY")  # noqa: F405
DATABASES = {"default": env.db("DATABASE_URL")}  # noqa: F405
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Produção exige PostgreSQL.")
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])  # noqa: F405
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
