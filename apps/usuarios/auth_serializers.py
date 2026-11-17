from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auditoria.services import registrar_evento


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        dados = super().validate(attrs)
        registrar_evento(
            acao="LOGIN_SUCESSO",
            ator=self.user,
            entidade_id=self.user.pk,
            request=self.context.get("request"),
        )
        return dados


class RefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except get_user_model().DoesNotExist as exc:
            raise AuthenticationFailed("Conta indisponível.") from exc


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate_refresh(self, value):
        try:
            token = RefreshToken(value)
        except TokenError as exc:
            raise InvalidToken("Refresh inválido ou expirado.") from exc
        if str(token.get("user_id")) != str(self.context["request"].user.pk):
            raise PermissionDenied("O refresh não pertence ao usuário autenticado.")
        return token
