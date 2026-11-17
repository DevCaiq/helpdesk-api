from django.db import transaction
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.auditoria.services import registrar_evento
from apps.core.serializers import ErroSerializer

from .auth_serializers import (
    LoginSerializer,
    LogoutSerializer,
    RefreshSerializer,
    TokenPairSerializer,
)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        tags=["Autenticação"],
        summary="Entrar com e-mail e senha",
        responses={
            200: TokenPairSerializer,
            400: ErroSerializer,
            401: ErroSerializer,
            429: ErroSerializer,
        },
        examples=[
            OpenApiExample(
                "Par de tokens",
                value={"access": "<access>", "refresh": "<refresh>"},
                response_only=True,
            )
        ],
    )
    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().post(request, *args, **kwargs)
        except APIException:
            registrar_evento(acao="LOGIN_FALHA", request=request)
            raise


class RefreshView(TokenRefreshView):
    serializer_class = RefreshSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "refresh"

    @extend_schema(
        tags=["Autenticação"],
        summary="Renovar e rotacionar tokens",
        description="Retorna novo access e refresh; o refresh anterior não pode ser reutilizado.",
        responses={
            200: TokenPairSerializer,
            400: ErroSerializer,
            401: ErroSerializer,
            429: ErroSerializer,
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "escrita"

    @extend_schema(
        tags=["Autenticação"],
        summary="Revogar o refresh do usuário autenticado",
        description="Exige access Bearer. O access existente continua válido até expirar.",
        responses={204: None, 400: ErroSerializer, 401: ErroSerializer, 403: ErroSerializer},
    )
    @transaction.atomic
    def post(self, request):
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        entrada.validated_data["refresh"].blacklist()
        registrar_evento(
            acao="LOGOUT", ator=request.user, entidade_id=request.user.pk, request=request
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
