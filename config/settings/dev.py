from .base import *  # noqa: F403
from .base import BASE_DIR, env

env.read_env(BASE_DIR / ".env")  # noqa: F405
SECRET_KEY = env("SECRET_KEY", default="local-only-change-before-deploy-0123456789")  # noqa: F405
DEBUG = env.bool("DEBUG", default=True)  # noqa: F405
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])  # noqa: F405
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / env("SQLITE_PATH", default="db.sqlite3"),
    }
}
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
ALLOW_DEMO_SEED = True
