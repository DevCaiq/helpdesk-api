from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.chamados.selectors import visiveis
from apps.core.throttling import EscritaThrottleMixin
from apps.usuarios.permissions import IsGestor

from .models import AlertaSLA, PoliticaSLA
from .serializers import AlertaSerializer, PoliticaEntradaSerializer, PoliticaSerializer
from .services import alterar_politica


@extend_schema_view(get=extend_schema(tags=["SLA"], summary="Listar políticas (Gestor)"))
class PoliticasView(EscritaThrottleMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsGestor]
    serializer_class = PoliticaSerializer
    queryset = PoliticaSLA.objects.order_by("id")


@extend_schema_view(get=extend_schema(tags=["SLA"], summary="Consultar política (Gestor)"))
class PoliticaView(EscritaThrottleMixin, generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsGestor]
    serializer_class = PoliticaSerializer
    queryset = PoliticaSLA.objects.all()

    @extend_schema(
        tags=["SLA"],
        summary="Alterar prazo para novos chamados (Gestor)",
        request=PoliticaEntradaSerializer,
        responses=PoliticaSerializer,
    )
    def patch(self, request, *args, **kwargs):
        politica = self.get_object()
        entrada = PoliticaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        politica = alterar_politica(
            politica=politica,
            minutos_resolucao=entrada.validated_data["minutos_resolucao"],
            ator=request.user,
            request=request,
        )
        return Response(PoliticaSerializer(politica).data)


class PodeVerAlertas(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and request.user.is_active
            and (
                request.user.perfil == "GESTOR"
                or (request.user.perfil == "ANALISTA" and request.user.nivel == "N1")
            )
        )


@extend_schema_view(
    get=extend_schema(tags=["Alertas"], summary="Consultar alertas históricos de SLA")
)
class AlertasView(EscritaThrottleMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated, PodeVerAlertas]
    serializer_class = AlertaSerializer
    filterset_fields = ["tipo", "chamado", "triagem_pendente"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AlertaSLA.objects.none()
        chamados = visiveis(self.request.user)
        if self.request.user.perfil != "GESTOR":
            chamados = chamados.filter(nivel_atual="N1")
        return AlertaSLA.objects.filter(chamado_id__in=chamados.values_list("pk", flat=True))
