from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.sla.indicadores import indicadores
from apps.sla.models import CicloResolucao
from apps.sla.serializers import SlaSerializer
from apps.usuarios.serializers import StrictSerializer

from .choices import Impacto, Prioridade, Status, Urgencia
from .models import Categoria, Chamado, Comentario, EventoChamado, HistoricoStatus


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ("id", "nome", "ativa")
        read_only_fields = fields


class CategoriaEntradaSerializer(StrictSerializer):
    nome = serializers.CharField(max_length=100)
    ativa = serializers.BooleanField(required=False)


class CicloSerializer(serializers.ModelSerializer):
    class Meta:
        model = CicloResolucao
        fields = (
            "id",
            "inicio",
            "prazo",
            "minutos_aplicados",
            "prioridade",
            "resolvido_em",
            "encerrado_em",
            "resultado",
        )
        read_only_fields = fields


class ChamadoSerializer(serializers.ModelSerializer):
    ciclos = CicloSerializer(many=True, read_only=True)
    sla = serializers.SerializerMethodField()
    sla_status = serializers.SerializerMethodField()

    def valores_sla(self, obj):
        cache = self.context.setdefault("indicadores_sla", {})
        if obj.pk not in cache:
            agora = self.context.setdefault("agora_sla", timezone.now())
            cache[obj.pk] = indicadores(obj, agora)
        return cache[obj.pk]

    @extend_schema_field(SlaSerializer)
    def get_sla(self, obj):
        return self.valores_sla(obj)

    def get_sla_status(self, obj) -> str:
        return self.valores_sla(obj)["status"]

    class Meta:
        model = Chamado
        fields = (
            "id",
            "titulo",
            "descricao",
            "categoria",
            "solicitante",
            "responsavel",
            "impacto",
            "urgencia",
            "prioridade",
            "status",
            "nivel_atual",
            "aberto_em",
            "primeira_resposta_em",
            "prazo_primeira_resposta",
            "resolvido_em",
            "fechado_em",
            "ciclos",
            "sla",
            "sla_status",
            "triado_em",
            "triado_por",
        )
        read_only_fields = fields


class AbrirChamadoSerializer(StrictSerializer):
    titulo = serializers.CharField(max_length=200)
    descricao = serializers.CharField(max_length=10000)
    categoria = serializers.PrimaryKeyRelatedField(queryset=Categoria.objects.filter(ativa=True))
    impacto = serializers.ChoiceField(choices=Impacto.choices)
    urgencia = serializers.ChoiceField(choices=Urgencia.choices)


class EditarChamadoSerializer(StrictSerializer):
    titulo = serializers.CharField(max_length=200, required=False)
    descricao = serializers.CharField(max_length=10000, required=False)
    categoria = serializers.PrimaryKeyRelatedField(
        queryset=Categoria.objects.filter(ativa=True), required=False
    )


class ComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comentario
        fields = ("id", "autor", "texto", "interno", "criado_em")
        read_only_fields = fields


class ComentarioEntradaSerializer(StrictSerializer):
    texto = serializers.CharField(max_length=10000)
    interno = serializers.BooleanField(default=False)


class HistoricoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricoStatus
        fields = ("id", "status_anterior", "status_novo", "autor", "motivo", "criado_em")
        read_only_fields = fields


class AssumirSerializer(StrictSerializer):
    pass


class MotivoSerializer(StrictSerializer):
    motivo = serializers.CharField(max_length=10000)


class TransicaoSerializer(MotivoSerializer):
    status = serializers.ChoiceField(choices=Status.choices)


class ReatribuirSerializer(StrictSerializer):
    responsavel = serializers.IntegerField(min_value=1)


class PrioridadeEntradaSerializer(MotivoSerializer):
    prioridade = serializers.ChoiceField(choices=Prioridade.choices)


class EventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventoChamado
        fields = ("id", "tipo", "autor", "motivo", "dados", "criado_em")
        read_only_fields = fields
