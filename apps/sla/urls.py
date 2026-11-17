from django.urls import path

from .views import AlertasView, PoliticasView, PoliticaView

urlpatterns = [
    path("sla/politicas/", PoliticasView.as_view(), name="politicas-sla"),
    path("sla/politicas/<int:pk>/", PoliticaView.as_view(), name="politica-sla"),
    path("alertas/", AlertasView.as_view(), name="alertas-sla"),
]
