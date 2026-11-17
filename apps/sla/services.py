from datetime import timedelta

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.chamados.choices import Impacto, Prioridade, Urgencia

from .indicadores import prazo_efetivo
from .models import CicloResolucao, PausaSLA, PoliticaSLA


def calcular_prioridade(impacto, urgencia):
    matriz = [
        [Prioridade.CRITICA, Prioridade.ALTA, Prioridade.MEDIA],
        [Prioridade.ALTA, Prioridade.MEDIA, Prioridade.BAIXA],
        [Prioridade.MEDIA, Prioridade.BAIXA, Prioridade.BAIXA],
    ]
    return matriz[Impacto.values.index(impacto)][Urgencia.values.index(urgencia)]


def snapshot_politicas():
    snapshot = dict(PoliticaSLA.objects.values_list("prioridade", "minutos_resolucao"))
    if set(snapshot) != set(Prioridade.values):
        raise ValidationError("Políticas de SLA incompletas; solicite configuração ao Gestor.")
    return snapshot


def iniciar_ciclo(chamado, agora):
    minutos = chamado.sla_snapshot[chamado.prioridade]
    return CicloResolucao.objects.create(
        chamado=chamado,
        inicio=agora,
        prazo=agora + timedelta(minutes=minutos),
        minutos_aplicados=minutos,
        prioridade=chamado.prioridade,
    )


def ciclo_ativo(chamado):
    return chamado.ciclos.get(encerrado_em__isnull=True)


def pausar(chamado, agora):
    PausaSLA.objects.create(ciclo=ciclo_ativo(chamado), inicio=agora)


def retomar(chamado, agora):
    ciclo = ciclo_ativo(chamado)
    pausa = ciclo.pausas.get(fim__isnull=True)
    pausa.fim = agora
    pausa.save(update_fields=["fim"])
    ciclo.prazo += agora - pausa.inicio
    ciclo.save(update_fields=["prazo"])


def encerrar_ciclo(chamado, agora, cancelado=False):
    ciclo = ciclo_ativo(chamado)
    if not cancelado:
        registrar_violacao(ciclo, agora)
    ciclo.encerrado_em = agora
    if cancelado:
        ciclo.resultado = "NAO_APLICAVEL"
    else:
        ciclo.resolvido_em = agora
        ciclo.resultado = (
            "CUMPRIDO" if agora <= ciclo.prazo and ciclo.violado_em is None else "VIOLADO"
        )
    ciclo.save()
    finalizar_primeira_resposta(chamado, agora, cancelado=cancelado)


def finalizar_primeira_resposta(chamado, agora, cancelado=False):
    if chamado.primeira_resposta_resultado:
        return
    if chamado.primeira_resposta_em:
        fim = chamado.primeira_resposta_em
        resultado = "CUMPRIDO" if fim <= chamado.prazo_primeira_resposta else "VIOLADO"
    else:
        fim = agora
        resultado = "NAO_APLICAVEL" if cancelado else "VIOLADO"
    chamado.primeira_resposta_finalizada_em = fim
    chamado.primeira_resposta_resultado = resultado
    chamado.save(
        update_fields=[
            "primeira_resposta_em",
            "primeira_resposta_finalizada_em",
            "primeira_resposta_resultado",
        ]
    )


def registrar_violacao(ciclo, agora):
    if (
        ciclo.encerrado_em is None
        and ciclo.violado_em is None
        and agora > prazo_efetivo(ciclo, agora)
    ):
        ciclo.violado_em = agora
        ciclo.save(update_fields=["violado_em"])


def recalcular_prioridade(chamado, prioridade, agora):
    ciclo = ciclo_ativo(chamado)
    registrar_violacao(ciclo, agora)
    pausas = ciclo.pausas.filter(fim__isnull=False)
    total_pausas = sum((p.fim - p.inicio for p in pausas), timedelta())
    ciclo.minutos_aplicados = chamado.sla_snapshot[prioridade]
    ciclo.prioridade = prioridade
    ciclo.prazo = ciclo.inicio + timedelta(minutes=ciclo.minutos_aplicados) + total_pausas
    ciclo.save(update_fields=["minutos_aplicados", "prioridade", "prazo"])
    registrar_violacao(ciclo, agora)


@transaction.atomic
def alterar_politica(*, politica, minutos_resolucao, ator, request=None):
    from apps.auditoria.services import registrar_evento
    from apps.usuarios.services import exigir_gestor

    exigir_gestor(ator)
    politica = PoliticaSLA.objects.select_for_update().get(pk=politica.pk)
    antes = {"prioridade": politica.prioridade, "minutos_resolucao": politica.minutos_resolucao}
    politica.minutos_resolucao = minutos_resolucao
    politica.full_clean()
    politica.save(update_fields=["minutos_resolucao"])
    registrar_evento(
        acao="POLITICA_SLA_ALTERADA",
        ator=ator,
        entidade="politica_sla",
        entidade_id=politica.pk,
        antes=antes,
        depois={"prioridade": politica.prioridade, "minutos_resolucao": politica.minutos_resolucao},
        request=request,
    )
    return politica
