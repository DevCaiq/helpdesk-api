from .test import *  # noqa: F403

DATABASES = {"default": env.db("DATABASE_URL")}  # noqa: F405
