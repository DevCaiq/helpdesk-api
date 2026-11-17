from django.db import models


class Status(models.TextChoices):
    ABERTO = "ABERTO", "Aberto"
    EM_ATENDIMENTO = "EM_ATENDIMENTO", "Em atendimento"
    AGUARDANDO_SOLICITANTE = "AGUARDANDO_SOLICITANTE", "Aguardando solicitante"
    RESOLVIDO = "RESOLVIDO", "Resolvido"
    REABERTO = "REABERTO", "Reaberto"
    FECHADO = "FECHADO", "Fechado"
    CANCELADO = "CANCELADO", "Cancelado"


class Prioridade(models.TextChoices):
    CRITICA = "CRITICA", "Crítica"
    ALTA = "ALTA", "Alta"
    MEDIA = "MEDIA", "Média"
    BAIXA = "BAIXA", "Baixa"


class Impacto(models.TextChoices):
    ALTO = "ALTO", "Alto"
    MEDIO = "MEDIO", "Médio"
    BAIXO = "BAIXO", "Baixo"


class Urgencia(models.TextChoices):
    ALTA = "ALTA", "Alta"
    MEDIA = "MEDIA", "Média"
    BAIXA = "BAIXA", "Baixa"
