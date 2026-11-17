from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Usuario


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - {key for key, field in self.fields.items() if not field.read_only}
            if unknown:
                raise serializers.ValidationError(
                    {key: "Campo não permitido." for key in sorted(unknown)}
                )
        return super().to_internal_value(data)


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ("id", "email", "nome", "perfil", "nivel", "is_active")
        read_only_fields = fields


class CadastroSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)
    nome = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate_email(self, value):
        value = Usuario.objects.normalize_email(value)
        if Usuario.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("E-mail já cadastrado.")
        return value

    def validate(self, attrs):
        try:
            validate_password(attrs["password"], Usuario(email=attrs["email"], nome=attrs["nome"]))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs


class EquipeSerializer(CadastroSerializer):
    perfil = serializers.ChoiceField(choices=[Usuario.Perfil.ANALISTA, Usuario.Perfil.GESTOR])
    nivel = serializers.ChoiceField(choices=Usuario.Nivel.choices, allow_null=True, required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        validar_perfil_nivel(attrs["perfil"], attrs.get("nivel"))
        return attrs


def validar_perfil_nivel(perfil, nivel):
    if (perfil == "ANALISTA") != (nivel in ("N1", "N2")) or (
        perfil != "ANALISTA" and nivel is not None
    ):
        raise serializers.ValidationError(
            {"nivel": "Nível é obrigatório e exclusivo para Analista."}
        )


class AlterarUsuarioSerializer(StrictSerializer):
    nome = serializers.CharField(max_length=150, required=False)
    perfil = serializers.ChoiceField(choices=Usuario.Perfil.choices, required=False)
    nivel = serializers.ChoiceField(choices=Usuario.Nivel.choices, allow_null=True, required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        user = self.instance
        validar_perfil_nivel(attrs.get("perfil", user.perfil), attrs.get("nivel", user.nivel))
        return attrs
