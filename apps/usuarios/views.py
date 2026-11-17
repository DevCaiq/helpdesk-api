from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.serializers import ErroSerializer

from .models import Usuario
from .permissions import IsGestor
from .serializers import (
    AlterarUsuarioSerializer,
    CadastroSerializer,
    EquipeSerializer,
    UsuarioSerializer,
)
from .services import alterar_usuario, criar_usuario


@extend_schema_view(get=extend_schema(tags=["Usuários"], summary="Listar usuários (Gestor)"))
class UsuariosView(generics.ListCreateAPIView):
    serializer_class = UsuarioSerializer
    queryset = Usuario.objects.order_by("id")
    throttle_classes = [ScopedRateThrottle]

    def get_permissions(self):
        return [AllowAny()] if self.request.method == "POST" else [IsAuthenticated(), IsGestor()]

    def get_throttles(self):
        self.throttle_scope = "cadastro" if self.request.method == "POST" else "leitura"
        return super().get_throttles()

    @extend_schema(
        tags=["Usuários"],
        summary="Cadastrar solicitante",
        request=CadastroSerializer,
        responses={201: UsuarioSerializer, 400: ErroSerializer, 429: ErroSerializer},
        auth=[],
    )
    def post(self, request, *args, **kwargs):
        entrada = CadastroSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        usuario = criar_usuario(dados=entrada.validated_data, request=request)
        return Response(UsuarioSerializer(usuario).data, status=status.HTTP_201_CREATED)


@extend_schema_view(get=extend_schema(tags=["Usuários"], summary="Consultar meu perfil"))
class MeView(generics.RetrieveAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class EquipeView(generics.GenericAPIView):
    serializer_class = EquipeSerializer
    permission_classes = [IsAuthenticated, IsGestor]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "escrita"

    @extend_schema(
        tags=["Usuários"],
        summary="Criar Analista ou Gestor (Gestor)",
        responses={201: UsuarioSerializer, 400: ErroSerializer, 403: ErroSerializer},
    )
    def post(self, request):
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        usuario = criar_usuario(dados=entrada.validated_data, ator=request.user, request=request)
        return Response(UsuarioSerializer(usuario).data, status=status.HTTP_201_CREATED)


class AlterarUsuarioView(generics.GenericAPIView):
    queryset = Usuario.objects.all()
    serializer_class = AlterarUsuarioSerializer
    permission_classes = [IsAuthenticated, IsGestor]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "escrita"

    @extend_schema(
        tags=["Usuários"],
        summary="Alterar perfil, nível, nome ou ativação (Gestor)",
        responses={
            200: UsuarioSerializer,
            400: ErroSerializer,
            403: ErroSerializer,
            404: ErroSerializer,
        },
    )
    def patch(self, request, *args, **kwargs):
        usuario = self.get_object()
        entrada = self.get_serializer(instance=usuario, data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        usuario = alterar_usuario(
            usuario=usuario, dados=entrada.validated_data, ator=request.user, request=request
        )
        return Response(UsuarioSerializer(usuario).data)
