from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import health, ready

urlpatterns = [
    path("api/v1/", include("apps.usuarios.urls")),
    path("api/v1/", include("apps.chamados.urls")),
    path("api/v1/", include("apps.sla.urls")),
    path("api/v1/", include("apps.metricas.urls")),
    path("api/v1/", include("apps.auditoria.urls")),
    path("health/", health),
    path("ready/", ready),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
