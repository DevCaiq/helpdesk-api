from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.core.serializers import ErroSerializer
from apps.core.throttling import EscritaThrottleMixin
from apps.usuarios.permissions import IsGestor

from .models import LogAuditoria
from .selectors import consultar_logs
from .serializers import ConsultaAuditoriaSerializer, LogAuditoriaSerializer


@extend_schema_view(
    get=extend_schema(
        tags=["Auditoria"],
        summary="Consultar auditoria (Gestor)",
        parameters=[ConsultaAuditoriaSerializer],
        description=(
            "Somente leitura, paginado20/máximo100, ordem -criado_em,-id. "
            "Intervalo [inicio,fim) com fuso; sistema=true filtra ator nulo."
        ),
        responses={
            200: LogAuditoriaSerializer(many=True),
            400: ErroSerializer,
            401: ErroSerializer,
            403: ErroSerializer,
        },
    )
)
class AuditoriaView(EscritaThrottleMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsGestor]
    serializer_class = LogAuditoriaSerializer
    filter_backends = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LogAuditoria.objects.none()
        entrada = ConsultaAuditoriaSerializer(data=self.request.query_params)
        entrada.is_valid(raise_exception=True)
        return consultar_logs(entrada.validated_data)


@extend_schema_view(
    get=extend_schema(
        tags=["Auditoria"],
        summary="Consultar evento de auditoria (Gestor)",
        responses={
            200: LogAuditoriaSerializer,
            401: ErroSerializer,
            403: ErroSerializer,
            404: ErroSerializer,
        },
    )
)
class AuditoriaDetalheView(EscritaThrottleMixin, generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsGestor]
    serializer_class = LogAuditoriaSerializer
    queryset = LogAuditoria.objects.all()
