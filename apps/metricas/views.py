from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.periodos import PeriodoSerializer
from apps.core.serializers import ErroSerializer
from apps.core.throttling import EscritaThrottleMixin
from apps.usuarios.permissions import IsGestor

from . import selectors
from .serializers import SlaMetricasSerializer, VolumeSerializer


class MetricasBaseView(EscritaThrottleMixin, generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsGestor]

    def periodo(self):
        entrada = PeriodoSerializer(data=self.request.query_params)
        entrada.is_valid(raise_exception=True)
        return entrada.validated_data


class VolumeView(MetricasBaseView):
    serializer_class = VolumeSerializer

    @extend_schema(
        tags=["Métricas"],
        summary="Volume por data de abertura (Gestor)",
        parameters=[PeriodoSerializer],
        responses={
            200: VolumeSerializer,
            400: ErroSerializer,
            401: ErroSerializer,
            403: ErroSerializer,
        },
        description=(
            "Intervalo [inicio,fim) ISO8601 com fuso. "
            "Agrupa estado atual; não duplica chamados reabertos."
        ),
    )
    def get(self, request):
        return Response(self.get_serializer(selectors.volume(**self.periodo())).data)


class SlaMetricasView(MetricasBaseView):
    serializer_class = SlaMetricasSerializer

    @extend_schema(
        tags=["Métricas"],
        summary="Cumprimento de SLA por conclusão (Gestor)",
        parameters=[PeriodoSerializer],
        responses={
            200: SlaMetricasSerializer,
            400: ErroSerializer,
            401: ErroSerializer,
            403: ErroSerializer,
        },
        description=(
            "Primeira resposta por chamado; resolução por ciclo. "
            "Resultados NAO_APLICAVEL não entram no denominador. "
            "Taxa null quando não há obrigações aplicáveis concluídas."
        ),
    )
    def get(self, request):
        return Response(self.get_serializer(selectors.sla(**self.periodo())).data)
