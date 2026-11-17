from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.core.exceptions import Conflito
from apps.sla import services as sla

from .choices import Status
from .models import EventoChamado
from .services import auditar, bloqueado, exigir_atendimento, snapshot

ATIVOS = (Status.ABERTO, Status.EM_ATENDIMENTO, Status.REABERTO)


@transaction.atomic
def triar_chamado(*, chamado_id, ator, motivo, request=None):
    chamado = bloqueado(chamado_id, ator)
    if ator.perfil != "ANALISTA" or ator.nivel != "N1" or ator.pk == chamado.solicitante_id:
        raise PermissionDenied("Triagem exige N1 e não pode ser feita pelo solicitante.")
    if chamado.nivel_atual != "N1" or chamado.status not in ATIVOS or chamado.triado_em is not None:
        raise Conflito("Chamado indisponível ou já triado.")
    if chamado.responsavel_id is not None and chamado.responsavel_id != ator.pk:
        raise PermissionDenied("Somente N1 responsável pode triar chamado atribuído.")
    antes = snapshot(chamado)
    chamado.triado_por = ator
    chamado.triado_em = timezone.now()
    chamado.save(update_fields=["triado_por", "triado_em"])
    evento = EventoChamado.objects.create(
        chamado=chamado, tipo="TRIAGEM", autor=ator, motivo=motivo
    )
    auditar(
        chamado,
        ator,
        "CHAMADO_TRIADO",
        request,
        antes=antes,
        depois={**snapshot(chamado), "triado_por_id": ator.pk, "evento_id": evento.pk},
    )
    return chamado


def escalar_bloqueado(chamado, *, ator, motivo, automatico=False, request=None):
    if chamado.nivel_atual != "N1" or chamado.status not in ATIVOS or chamado.triado_em is None:
        raise Conflito("Escalada exige chamado ativo em N1 com triagem concluída.")
    antes = snapshot(chamado)
    chamado.nivel_atual = "N2"
    chamado.responsavel = None
    chamado.save(update_fields=["nivel_atual", "responsavel"])
    evento = EventoChamado.objects.create(
        chamado=chamado,
        tipo="ESCALADO",
        autor=ator,
        motivo=motivo,
        dados={"nivel_origem": "N1", "nivel_destino": "N2", "automatico": automatico},
    )
    auditar(
        chamado,
        ator,
        "CHAMADO_ESCALADO",
        request,
        antes=antes,
        depois={**snapshot(chamado), "evento_id": evento.pk},
    )
    return chamado


@transaction.atomic
def escalar_chamado(*, chamado_id, ator, motivo, request=None):
    chamado = bloqueado(chamado_id, ator)
    if ator.pk == chamado.solicitante_id:
        raise PermissionDenied("Solicitante não pode escalar o próprio chamado.")
    if ator.perfil != "GESTOR":
        if ator.perfil != "ANALISTA" or ator.nivel != "N1":
            raise PermissionDenied("Escalada exige N1 ou Gestor.")
        if chamado.responsavel_id is not None and chamado.responsavel_id != ator.pk:
            raise PermissionDenied("Escalada exige responsável N1 ou Gestor.")
    return escalar_bloqueado(chamado, ator=ator, motivo=motivo, request=request)


@transaction.atomic
def alterar_prioridade(*, chamado_id, ator, prioridade, motivo, request=None):
    chamado = bloqueado(chamado_id, ator)
    exigir_atendimento(chamado, ator)
    if chamado.status == Status.RESOLVIDO:
        raise Conflito("Chamado resolvido não aceita repriorização.")
    if chamado.prioridade == prioridade:
        raise Conflito("Prioridade já aplicada.")
    ciclo = sla.ciclo_ativo(chamado)
    antes = {**snapshot(chamado), "prazo_resolucao": ciclo.prazo.isoformat()}
    sla.recalcular_prioridade(chamado, prioridade, timezone.now())
    chamado.prioridade = prioridade
    chamado.save(update_fields=["prioridade"])
    evento = EventoChamado.objects.create(
        chamado=chamado,
        tipo="PRIORIDADE_ALTERADA",
        autor=ator,
        motivo=motivo,
        dados={"prioridade_anterior": antes["prioridade"], "prioridade_nova": prioridade},
    )
    ciclo.refresh_from_db()
    auditar(
        chamado,
        ator,
        "PRIORIDADE_ALTERADA",
        request,
        antes=antes,
        depois={
            **snapshot(chamado),
            "prazo_resolucao": ciclo.prazo.isoformat(),
            "evento_id": evento.pk,
        },
    )
    return chamado
