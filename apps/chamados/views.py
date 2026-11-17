from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.serializers import ErroSerializer
from apps.core.throttling import EscritaThrottleMixin
from apps.usuarios.permissions import IsGestor

from . import services
from .filters import ChamadoFilter
from .models import Categoria, Comentario, HistoricoStatus
from .selectors import visiveis
from .serializers import (
    AbrirChamadoSerializer,
    AssumirSerializer,
    CategoriaEntradaSerializer,
    CategoriaSerializer,
    ChamadoSerializer,
    ComentarioEntradaSerializer,
    ComentarioSerializer,
    EditarChamadoSerializer,
    EventoSerializer,
    HistoricoSerializer,
    MotivoSerializer,
    PrioridadeEntradaSerializer,
    ReatribuirSerializer,
    TransicaoSerializer,
)
from .services_categorias import excluir_categoria, salvar_categoria
from .services_escalonamento import alterar_prioridade, escalar_chamado, triar_chamado


@extend_schema_view(
    list=extend_schema(tags=["Categorias"]),
    retrieve=extend_schema(tags=["Categorias"]),
    create=extend_schema(
        tags=["Categorias"],
        request=CategoriaEntradaSerializer,
        responses={201: CategoriaSerializer},
    ),
    update=extend_schema(
        tags=["Categorias"], request=CategoriaEntradaSerializer, responses=CategoriaSerializer
    ),
    partial_update=extend_schema(
        tags=["Categorias"], request=CategoriaEntradaSerializer, responses=CategoriaSerializer
    ),
    destroy=extend_schema(tags=["Categorias"], responses={204: None, 409: ErroSerializer}),
)
class CategoriaViewSet(EscritaThrottleMixin, viewsets.ModelViewSet):
    serializer_class = CategoriaSerializer
    queryset = Categoria.objects.all()

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            permissions.append(IsGestor())
        return permissions

    def create(self, request, *args, **kwargs):
        entrada = CategoriaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        obj = salvar_categoria(ator=request.user, dados=entrada.validated_data, request=request)
        return Response(CategoriaSerializer(obj).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        entrada = CategoriaEntradaSerializer(
            data=request.data, partial=kwargs.get("partial", False)
        )
        entrada.is_valid(raise_exception=True)
        obj = salvar_categoria(
            ator=request.user, dados=entrada.validated_data, categoria=obj, request=request
        )
        return Response(CategoriaSerializer(obj).data)

    def destroy(self, request, *args, **kwargs):
        excluir_categoria(ator=request.user, categoria=self.get_object(), request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VisibilidadeMixin:
    def get_queryset(self):
        return visiveis(self.request.user)


@extend_schema_view(get=extend_schema(tags=["Chamados"], summary="Listar fila visível"))
class ChamadosView(EscritaThrottleMixin, VisibilidadeMixin, generics.ListCreateAPIView):
    serializer_class = ChamadoSerializer
    filterset_class = ChamadoFilter
    filter_backends = [*generics.ListAPIView.filter_backends, SearchFilter, OrderingFilter]
    search_fields = ["titulo", "descricao"]
    ordering_fields = ["aberto_em", "id", "prioridade", "status"]
    ordering = ["-aberto_em", "-id"]

    @extend_schema(
        tags=["Chamados"],
        summary="Abrir chamado em N1",
        request=AbrirChamadoSerializer,
        responses={201: ChamadoSerializer, 400: ErroSerializer},
    )
    def post(self, request, *args, **kwargs):
        entrada = AbrirChamadoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        obj = services.abrir_chamado(
            ator=request.user, dados=entrada.validated_data, request=request
        )
        return Response(ChamadoSerializer(obj).data, status=status.HTTP_201_CREATED)


@extend_schema_view(get=extend_schema(tags=["Chamados"], summary="Consultar chamado visível"))
class ChamadoView(EscritaThrottleMixin, VisibilidadeMixin, generics.RetrieveAPIView):
    serializer_class = ChamadoSerializer

    @extend_schema(
        tags=["Chamados"],
        request=EditarChamadoSerializer,
        responses={200: ChamadoSerializer, 403: ErroSerializer, 409: ErroSerializer},
    )
    def patch(self, request, *args, **kwargs):
        self.get_object()
        entrada = EditarChamadoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        obj = services.editar_chamado(
            chamado_id=kwargs["pk"],
            ator=request.user,
            dados=entrada.validated_data,
            request=request,
        )
        return Response(ChamadoSerializer(obj).data)


class AcaoView(EscritaThrottleMixin, VisibilidadeMixin, generics.GenericAPIView):
    operacao = None
    serializers = {
        "assumir": AssumirSerializer,
        "transicionar": TransicaoSerializer,
        "reabrir": MotivoSerializer,
        "reatribuir": ReatribuirSerializer,
        "triar": MotivoSerializer,
        "escalar": MotivoSerializer,
        "prioridade": PrioridadeEntradaSerializer,
    }

    def get_serializer_class(self):
        return self.serializers[self.operacao]

    @extend_schema(
        tags=["Atendimento"],
        responses={
            200: ChamadoSerializer,
            400: ErroSerializer,
            403: ErroSerializer,
            404: ErroSerializer,
            409: ErroSerializer,
        },
    )
    def post(self, request, *args, **kwargs):
        self.get_object()
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = dict(entrada.validated_data)
        if self.operacao == "reatribuir":
            dados["responsavel_id"] = dados.pop("responsavel")
        service = {
            "assumir": services.assumir_chamado,
            "transicionar": services.transicionar_chamado,
            "reabrir": services.reabrir_chamado,
            "reatribuir": services.reatribuir_chamado,
            "triar": triar_chamado,
            "escalar": escalar_chamado,
            "prioridade": alterar_prioridade,
        }[self.operacao]
        obj = service(chamado_id=kwargs["pk"], ator=request.user, request=request, **dados)
        return Response(ChamadoSerializer(obj).data)


@extend_schema_view(get=extend_schema(tags=["Comentários"]))
class ComentariosView(EscritaThrottleMixin, generics.ListCreateAPIView):
    serializer_class = ComentarioSerializer

    def chamado(self):
        return get_object_or_404(visiveis(self.request.user), pk=self.kwargs["pk"])

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Comentario.objects.none()
        chamado = self.chamado()
        comentarios = chamado.comentarios.all()
        if chamado.solicitante_id == self.request.user.pk:
            comentarios = comentarios.filter(interno=False)
        return comentarios

    @extend_schema(
        tags=["Comentários"],
        request=ComentarioEntradaSerializer,
        responses={201: ComentarioSerializer, 403: ErroSerializer, 409: ErroSerializer},
    )
    def post(self, request, *args, **kwargs):
        self.chamado()
        entrada = ComentarioEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        comentario = services.comentar(
            chamado_id=kwargs["pk"], ator=request.user, request=request, **entrada.validated_data
        )
        return Response(ComentarioSerializer(comentario).data, status=status.HTTP_201_CREATED)


@extend_schema_view(get=extend_schema(tags=["Histórico"]))
class HistoricoView(generics.ListAPIView):
    serializer_class = HistoricoSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return HistoricoStatus.objects.none()
        chamado = get_object_or_404(visiveis(self.request.user), pk=self.kwargs["pk"])
        return chamado.historico.all()


@extend_schema_view(
    get=extend_schema(tags=["Histórico"], summary="Eventos internos de atendimento (equipe)")
)
class EventosView(generics.ListAPIView):
    serializer_class = EventoSerializer

    def get_queryset(self):
        from .models import EventoChamado

        if getattr(self, "swagger_fake_view", False):
            return EventoChamado.objects.none()
        chamado = get_object_or_404(visiveis(self.request.user), pk=self.kwargs["pk"])
        if chamado.solicitante_id == self.request.user.pk or self.request.user.perfil not in (
            "ANALISTA",
            "GESTOR",
        ):
            raise PermissionDenied(
                "Eventos internos são exclusivos da equipe, exceto solicitante do chamado."
            )
        return chamado.eventos.all()
