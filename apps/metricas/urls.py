from django.urls import path

from .views import SlaMetricasView, VolumeView

urlpatterns = [
    path("metricas/volume/", VolumeView.as_view(), name="metricas-volume"),
    path("metricas/sla/", SlaMetricasView.as_view(), name="metricas-sla"),
]
