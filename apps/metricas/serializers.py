from rest_framework import serializers

from apps.chamados.choices import Prioridade, Status


class PeriodoSaidaSerializer(serializers.Serializer):
    inicio = serializers.DateTimeField(allow_null=True)
    fim = serializers.DateTimeField(allow_null=True)


class GrupoStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Status.choices)
    total = serializers.IntegerField()


class GrupoNivelSerializer(serializers.Serializer):
    nivel = serializers.CharField()
    total = serializers.IntegerField()


class GrupoPrioridadeSerializer(serializers.Serializer):
    prioridade = serializers.ChoiceField(choices=Prioridade.choices)
    total = serializers.IntegerField()


class GrupoCategoriaSerializer(serializers.Serializer):
    categoria_id = serializers.IntegerField()
    nome = serializers.CharField()
    total = serializers.IntegerField()


class VolumeSerializer(serializers.Serializer):
    periodo = PeriodoSaidaSerializer()
    base_periodo = serializers.CharField()
    total = serializers.IntegerField()
    por_status = GrupoStatusSerializer(many=True)
    por_nivel = GrupoNivelSerializer(many=True)
    por_prioridade = GrupoPrioridadeSerializer(many=True)
    por_categoria = GrupoCategoriaSerializer(many=True)


class ResumoObrigacaoSerializer(serializers.Serializer):
    cumpridos = serializers.IntegerField()
    violados = serializers.IntegerField()
    nao_aplicaveis = serializers.IntegerField()
    total_concluidos = serializers.IntegerField()
    numerador = serializers.IntegerField()
    denominador = serializers.IntegerField()
    taxa_cumprimento_percentual = serializers.FloatField(allow_null=True)


class SlaMetricasSerializer(serializers.Serializer):
    periodo = PeriodoSaidaSerializer()
    base_periodo = serializers.CharField()
    primeira_resposta = ResumoObrigacaoSerializer()
    resolucao = ResumoObrigacaoSerializer()
