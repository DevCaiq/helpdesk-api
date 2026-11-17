from rest_framework import serializers

from apps.usuarios.serializers import StrictSerializer

from .indicadores import ESTADOS
from .models import AlertaSLA, PoliticaSLA


class IndicadorSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ESTADOS)
    percentual_consumido = serializers.FloatField()
    prazo = serializers.DateTimeField()
    violado = serializers.BooleanField()
    pausado = serializers.BooleanField()


class SlaSerializer(serializers.Serializer):
    primeira_resposta = IndicadorSerializer()
    resolucao = IndicadorSerializer()
    status = serializers.ChoiceField(choices=ESTADOS)


class PoliticaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoliticaSLA
        fields = ("id", "prioridade", "minutos_resolucao")
        read_only_fields = fields


class PoliticaEntradaSerializer(StrictSerializer):
    minutos_resolucao = serializers.IntegerField(min_value=1, max_value=525600)


class AlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertaSLA
        fields = ("id", "chamado", "ciclo", "tipo", "triagem_pendente", "criado_em")
        read_only_fields = fields
