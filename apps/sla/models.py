from django.db import models

from apps.chamados.choices import Prioridade
from apps.chamados.models import RegistroImutavel


class PoliticaSLA(models.Model):
    prioridade = models.CharField(max_length=7, choices=Prioridade, unique=True)
    minutos_resolucao = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(minutos_resolucao__gt=0), name="politica_prazo_positivo"
            ),
            models.CheckConstraint(
                condition=models.Q(prioridade__in=Prioridade.values),
                name="politica_prioridade_valida",
            ),
        ]


class CicloResolucao(models.Model):
    chamado = models.ForeignKey("chamados.Chamado", on_delete=models.PROTECT, related_name="ciclos")
    inicio = models.DateTimeField()
    prazo = models.DateTimeField(db_index=True)
    minutos_aplicados = models.PositiveIntegerField()
    prioridade = models.CharField(max_length=7, choices=Prioridade)
    resolvido_em = models.DateTimeField(null=True, blank=True)
    encerrado_em = models.DateTimeField(null=True, blank=True)
    resultado = models.CharField(max_length=14, blank=True)
    violado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["chamado"],
                condition=models.Q(encerrado_em__isnull=True),
                name="ciclo_aberto_unico",
            ),
            models.CheckConstraint(
                condition=models.Q(prazo__gte=models.F("inicio")), name="ciclo_prazo_coerente"
            ),
        ]


class PausaSLA(models.Model):
    ciclo = models.ForeignKey(CicloResolucao, on_delete=models.PROTECT, related_name="pausas")
    inicio = models.DateTimeField()
    fim = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["inicio", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["ciclo"], condition=models.Q(fim__isnull=True), name="pausa_aberta_unica"
            ),
            models.CheckConstraint(
                condition=models.Q(fim__isnull=True) | models.Q(fim__gte=models.F("inicio")),
                name="pausa_datas_coerentes",
            ),
        ]


class AlertaSLA(RegistroImutavel):
    class Tipo(models.TextChoices):
        CRITICO_SEM_RESPONSAVEL = "CRITICO_SEM_RESPONSAVEL", "Crítico sem responsável"
        RESOLUCAO_EM_RISCO = "RESOLUCAO_EM_RISCO", "Resolução em risco"
        PRIMEIRA_RESPOSTA_EM_RISCO = "PRIMEIRA_RESPOSTA_EM_RISCO", "Primeira resposta em risco"

    chamado = models.ForeignKey(
        "chamados.Chamado", on_delete=models.PROTECT, related_name="alertas"
    )
    ciclo = models.ForeignKey(CicloResolucao, on_delete=models.PROTECT, related_name="alertas")
    tipo = models.CharField(max_length=30, choices=Tipo)
    triagem_pendente = models.BooleanField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["ciclo", "tipo"], name="alerta_unico_por_ciclo_motivo")
        ]
