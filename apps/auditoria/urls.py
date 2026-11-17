from django.urls import path

from .views import AuditoriaDetalheView, AuditoriaView

urlpatterns = [
    path("auditoria/", AuditoriaView.as_view(), name="auditoria"),
    path("auditoria/<int:pk>/", AuditoriaDetalheView.as_view(), name="auditoria-detalhe"),
]
