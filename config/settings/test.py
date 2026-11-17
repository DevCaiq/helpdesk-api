from .base import *  # noqa: F403

# Chave pública exclusiva da suíte; esse settings nunca é usado em produção.
SECRET_KEY = "test-only-key-not-for-production-0123456789"  # nosec B105
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ALLOW_DEMO_SEED = True
MIDDLEWARE = [m for m in MIDDLEWARE if m != "whitenoise.middleware.WhiteNoiseMiddleware"]  # noqa: F405
