from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]
env = environ.Env()
DEBUG = False
ALLOWED_HOSTS = []
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "apps.usuarios",
    "apps.auditoria",
    "apps.chamados",
    "apps.sla",
    "apps.metricas",
    "apps.demo",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{name}"}
    for name in [
        "UserAttributeSimilarityValidator",
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    ]
]
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "usuarios.Usuario"
ALLOW_DEMO_SEED = False
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.ApiPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
        "refresh": "30/min",
        "cadastro": "10/hour",
        "escrita": "60/min",
        "leitura": "120/min",
    },
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Gestão de Chamados API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "PerfilUsuarioEnum": [
            ("SOLICITANTE", "Solicitante"),
            ("ANALISTA", "Analista"),
            ("GESTOR", "Gestor"),
        ],
        "PerfilEquipeEnum": ["ANALISTA", "GESTOR"],
        "StatusChamadoEnum": "apps.chamados.choices.Status.choices",
        "EstadoSlaEnum": [
            "NO_PRAZO",
            "EM_RISCO",
            "VENCIDO",
            "CUMPRIDO",
            "VIOLADO",
            "NAO_APLICAVEL",
        ],
        "TipoEventoEnum": [
            ("TRIAGEM", "Triagem"),
            ("PRIORIDADE_ALTERADA", "Prioridade alterada"),
            ("ESCALADO", "Escalado"),
        ],
        "TipoAlertaEnum": [
            ("CRITICO_SEM_RESPONSAVEL", "Crítico sem responsável"),
            ("RESOLUCAO_EM_RISCO", "Resolução em risco"),
            ("PRIMEIRA_RESPOSTA_EM_RISCO", "Primeira resposta em risco"),
        ],
    },
}
