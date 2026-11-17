from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.auditoria.models import ImutavelQuerySet

from .choices import Impacto, Prioridade, Status, Urgencia


class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome", "id"]

    def __str__(self):
        return self.nome


class Chamado(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(max_length=10000)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="chamados")
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="solicitacoes"
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="atendimentos",
    )
    impacto = models.CharField(max_length=5, choices=Impacto)
    urgencia = models.CharField(max_length=5, choices=Urgencia)
    prioridade = models.CharField(max_length=7, choices=Prioridade, db_index=True)
    status = models.CharField(max_length=23, choices=Status, default=Status.ABERTO, db_index=True)
    nivel_atual = models.CharField(
        max_length=2, choices=[("N1", "N1"), ("N2", "N2")], default="N1", db_index=True
    )
    sla_snapshot = models.JSONField()
    aberto_em = models.DateTimeField(db_index=True)
    primeira_resposta_em = models.DateTimeField(null=True, blank=True)
    primeira_resposta_resultado = models.CharField(max_length=14, blank=True)
    primeira_resposta_finalizada_em = models.DateTimeField(null=True, blank=True)
    prazo_primeira_resposta = models.DateTimeField()
    resolvido_em = models.DateTimeField(null=True, blank=True)
    fechado_em = models.DateTimeField(null=True, blank=True)
    ultima_interacao_solicitante_em = models.DateTimeField(null=True, blank=True)
    triado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="triagens",
    )
    triado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-aberto_em", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=Status.values), name="chamado_status_valido"
            ),
            models.CheckConstraint(
                condition=models.Q(nivel_atual__in=["N1", "N2"]), name="chamado_nivel_valido"
            ),
            models.CheckConstraint(
                condition=models.Q(prioridade__in=Prioridade.values),
                name="chamado_prioridade_valida",
            ),
            models.CheckConstraint(
                condition=models.Q(impacto__in=Impacto.values), name="chamado_impacto_valido"
            ),
            models.CheckConstraint(
                condition=models.Q(urgencia__in=Urgencia.values), name="chamado_urgencia_valida"
            ),
        ]


class RegistroImutavel(models.Model):
    objects = ImutavelQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding or self.pk is not None:
            raise ValidationError("Registro imutável.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Registro imutável.")


class Comentario(RegistroImutavel):
    chamado = models.ForeignKey(Chamado, on_delete=models.PROTECT, related_name="comentarios")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    texto = models.TextField(max_length=10000)
    interno = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em", "id"]


class HistoricoStatus(RegistroImutavel):
    chamado = models.ForeignKey(Chamado, on_delete=models.PROTECT, related_name="historico")
    status_anterior = models.CharField(max_length=23, choices=Status, blank=True)
    status_novo = models.CharField(max_length=23, choices=Status)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True
    )
    motivo = models.TextField(max_length=10000, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em", "id"]


class EventoChamado(RegistroImutavel):
    class Tipo(models.TextChoices):
        TRIAGEM = "TRIAGEM", "Triagem"
        PRIORIDADE_ALTERADA = "PRIORIDADE_ALTERADA", "Prioridade alterada"
        ESCALADO = "ESCALADO", "Escalado"

    chamado = models.ForeignKey(Chamado, on_delete=models.PROTECT, related_name="eventos")
    tipo = models.CharField(max_length=20, choices=Tipo)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True
    )
    motivo = models.TextField(max_length=10000)
    dados = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["chamado"],
                condition=models.Q(tipo="ESCALADO"),
                name="escalada_unica_chamado",
            )
        ]
