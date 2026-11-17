from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.periodos import PeriodoSerializer

from .models import LogAuditoria
from .services import ENTITY_FIELDS


class ConsultaAuditoriaSerializer(PeriodoSerializer):
    ator = serializers.IntegerField(min_value=1, required=False)
    sistema = serializers.BooleanField(required=False)
    acao = serializers.CharField(max_length=60, required=False)
    entidade = serializers.CharField(max_length=60, required=False)
    entidade_id = serializers.CharField(max_length=50, required=False)
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(min_value=1, required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get("sistema") and "ator" in attrs:
            raise serializers.ValidationError({"ator": "Não combine ator com sistema=true."})
        return attrs


def snapshot_publicavel(valor, entidade):
    if not isinstance(valor, dict):
        return {}
    permitidos = ENTITY_FIELDS.get(entidade, ())
    return {
        k: v
        for k, v in valor.items()
        if k in permitidos and (v is None or isinstance(v, (str, bool, int, float)))
    }


class LogAuditoriaSerializer(serializers.ModelSerializer):
    antes = serializers.SerializerMethodField()
    depois = serializers.SerializerMethodField()

    @extend_schema_field(serializers.JSONField)
    def get_antes(self, obj):
        return snapshot_publicavel(obj.antes, obj.entidade)

    @extend_schema_field(serializers.JSONField)
    def get_depois(self, obj):
        return snapshot_publicavel(obj.depois, obj.entidade)

    class Meta:
        model = LogAuditoria
        fields = (
            "id",
            "ator",
            "acao",
            "entidade",
            "entidade_id",
            "antes",
            "depois",
            "ip",
            "user_agent",
            "criado_em",
        )
        read_only_fields = fields
