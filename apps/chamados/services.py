from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.auditoria.services import registrar_evento
from apps.core.exceptions import Conflito
from apps.sla import services as sla
from apps.usuarios.models import Usuario

from .choices import Status
from .models import Chamado, Comentario, HistoricoStatus
from .selectors import visiveis

JANELA = timedelta(hours=48)


def snapshot(chamado):
    return {
        key: getattr(chamado, key)
        for key in ("status", "prioridade", "nivel_atual", "responsavel_id", "categoria_id")
    }


def auditar(chamado, ator, acao, request=None, antes=None, depois=None):
    registrar_evento(
        acao=acao,
        ator=ator,
        entidade="chamado",
        entidade_id=chamado.pk,
        antes=antes,
        depois=snapshot(chamado) if depois is None else depois,
        request=request,
    )


def elegivel_fechamento(chamado, agora):
    if chamado.status != Status.RESOLVIDO:
        return False
    ultima = chamado.ultima_interacao_solicitante_em or chamado.resolvido_em
    return agora >= chamado.resolvido_em + JANELA and agora >= ultima + JANELA


def modificavel(chamado, agora):
    if chamado.status in (Status.FECHADO, Status.CANCELADO) or elegivel_fechamento(chamado, agora):
        raise Conflito("Chamado encerrado definitivamente; alterações não são permitidas.")


def bloqueado(chamado_id, ator):
    chamado = get_object_or_404(
        visiveis(ator).prefetch_related(None).select_for_update(of=("self",)), pk=chamado_id
    )
    modificavel(chamado, timezone.now())
    return chamado


def exigir_atendimento(chamado, ator):
    if ator.perfil != "GESTOR" and not (
        ator.perfil == "ANALISTA"
        and chamado.responsavel_id == ator.pk
        and ator.nivel == chamado.nivel_atual
    ):
        raise PermissionDenied(
            "Somente o responsável compatível com o nível ou Gestor conduz atendimento."
        )


def mudar_status(chamado, destino, ator, motivo, request=None, antes=None):
    antes = snapshot(chamado) if antes is None else antes
    anterior = chamado.status
    chamado.status = destino
    chamado.save()
    HistoricoStatus.objects.create(
        chamado=chamado, status_anterior=anterior, status_novo=destino, autor=ator, motivo=motivo
    )
    auditar(chamado, ator, "STATUS_ALTERADO", request, antes=antes)


def adicionar_comentario(chamado, ator, texto, interno, agora, request=None):
    comentario = Comentario.objects.create(
        chamado=chamado, autor=ator, texto=texto, interno=interno
    )
    if (
        not interno
        and chamado.solicitante_id != ator.pk
        and ator.perfil in ("ANALISTA", "GESTOR")
        and chamado.primeira_resposta_em is None
        and not chamado.primeira_resposta_resultado
    ):
        chamado.primeira_resposta_em = agora
        sla.finalizar_primeira_resposta(chamado, agora)
    if not interno and chamado.solicitante_id == ator.pk and chamado.status == Status.RESOLVIDO:
        chamado.ultima_interacao_solicitante_em = agora
        chamado.save(update_fields=["ultima_interacao_solicitante_em"])
    auditar(
        chamado,
        ator,
        "COMENTARIO_CRIADO",
        request,
        depois={"comentario_id": comentario.pk, "interno": interno},
    )
    return comentario


@transaction.atomic
def abrir_chamado(*, ator, dados, request=None):
    agora = timezone.now()
    categoria = dados["categoria"]
    if not categoria.ativa:
        raise ValidationError({"categoria": "Categoria inativa."})
    chamado = Chamado.objects.create(
        titulo=dados["titulo"],
        descricao=dados["descricao"],
        categoria=categoria,
        impacto=dados["impacto"],
        urgencia=dados["urgencia"],
        solicitante=ator,
        prioridade=sla.calcular_prioridade(dados["impacto"], dados["urgencia"]),
        sla_snapshot=sla.snapshot_politicas(),
        aberto_em=agora,
        prazo_primeira_resposta=agora + timedelta(hours=2),
    )
    sla.iniciar_ciclo(chamado, agora)
    HistoricoStatus.objects.create(
        chamado=chamado, status_novo=Status.ABERTO, autor=ator, motivo="Abertura do chamado"
    )
    auditar(chamado, ator, "CHAMADO_ABERTO", request)
    return chamado


@transaction.atomic
def assumir_chamado(*, chamado_id, ator, request=None):
    chamado = bloqueado(chamado_id, ator)
    if ator.perfil != "ANALISTA" or ator.nivel != chamado.nivel_atual:
        raise PermissionDenied("Assunção exige Analista do nível do chamado.")
    if chamado.responsavel_id is not None or chamado.status not in (
        Status.ABERTO,
        Status.REABERTO,
        Status.EM_ATENDIMENTO,
    ):
        raise Conflito("Chamado já atribuído ou indisponível para assunção.")
    antes = snapshot(chamado)
    chamado.responsavel = ator
    if chamado.status != Status.EM_ATENDIMENTO:
        mudar_status(
            chamado,
            Status.EM_ATENDIMENTO,
            ator,
            "Analista assumiu o atendimento",
            request,
            antes=antes,
        )
    else:
        chamado.save(update_fields=["responsavel"])
    auditar(chamado, ator, "CHAMADO_ASSUMIDO", request, antes=antes)
    return chamado


@transaction.atomic
def editar_chamado(*, chamado_id, ator, dados, request=None):
    chamado = bloqueado(chamado_id, ator)
    if chamado.status == Status.RESOLVIDO:
        raise Conflito("Reabra o chamado antes de editar seu conteúdo.")
    if chamado.solicitante_id == ator.pk:
        if chamado.status != Status.ABERTO:
            raise PermissionDenied("Solicitante edita conteúdo somente em ABERTO.")
    else:
        exigir_atendimento(chamado, ator)
    if "categoria" in dados and not dados["categoria"].ativa:
        raise ValidationError({"categoria": "Categoria inativa."})
    antes = snapshot(chamado)
    for field in ("titulo", "descricao", "categoria"):
        if field in dados:
            setattr(chamado, field, dados[field])
    chamado.save()
    auditar(chamado, ator, "CHAMADO_EDITADO", request, antes=antes)
    return chamado


def reabrir_bloqueado(chamado, ator, motivo, agora, request=None):
    if chamado.status != Status.RESOLVIDO or agora >= chamado.resolvido_em + JANELA:
        raise Conflito("Reabertura exige chamado RESOLVIDO há menos de 48 horas.")
    if ator.pk != chamado.solicitante_id and ator.perfil != "GESTOR":
        raise PermissionDenied("Somente solicitante ou Gestor pode reabrir.")
    antes = snapshot(chamado)
    chamado.responsavel = None
    chamado.resolvido_em = None
    chamado.ultima_interacao_solicitante_em = None
    sla.iniciar_ciclo(chamado, agora)
    mudar_status(chamado, Status.REABERTO, ator, motivo, request, antes=antes)


@transaction.atomic
def reabrir_chamado(*, chamado_id, ator, motivo, request=None):
    chamado = bloqueado(chamado_id, ator)
    reabrir_bloqueado(chamado, ator, motivo, timezone.now(), request)
    return chamado


@transaction.atomic
def transicionar_chamado(*, chamado_id, ator, status, motivo, request=None):
    chamado = bloqueado(chamado_id, ator)
    agora = timezone.now()
    transicoes = {
        (Status.ABERTO, Status.CANCELADO),
        (Status.EM_ATENDIMENTO, Status.AGUARDANDO_SOLICITANTE),
        (Status.AGUARDANDO_SOLICITANTE, Status.EM_ATENDIMENTO),
        (Status.EM_ATENDIMENTO, Status.RESOLVIDO),
        (Status.RESOLVIDO, Status.FECHADO),
        (Status.RESOLVIDO, Status.REABERTO),
    }
    if (chamado.status, status) not in transicoes:
        raise Conflito("Transição inválida para o estado atual.")
    if status == Status.REABERTO:
        reabrir_bloqueado(chamado, ator, motivo, agora, request)
        return chamado
    if status in (Status.CANCELADO, Status.FECHADO):
        if ator.pk != chamado.solicitante_id and ator.perfil != "GESTOR":
            raise PermissionDenied(
                "Somente solicitante ou Gestor pode cancelar/confirmar fechamento."
            )
    else:
        exigir_atendimento(chamado, ator)
    if status == Status.AGUARDANDO_SOLICITANTE:
        if ator.pk == chamado.solicitante_id:
            raise PermissionDenied("Solicitante não pode solicitar informação a si próprio.")
        adicionar_comentario(chamado, ator, motivo, False, agora, request)
        sla.pausar(chamado, agora)
    elif chamado.status == Status.AGUARDANDO_SOLICITANTE:
        sla.retomar(chamado, agora)
    if status == Status.RESOLVIDO:
        adicionar_comentario(chamado, ator, motivo, False, agora, request)
        chamado.resolvido_em = agora
        chamado.ultima_interacao_solicitante_em = None
        sla.encerrar_ciclo(chamado, agora)
    elif status == Status.CANCELADO:
        sla.encerrar_ciclo(chamado, agora, cancelado=True)
    elif status == Status.FECHADO:
        chamado.fechado_em = agora
    mudar_status(chamado, status, ator, motivo, request)
    return chamado


@transaction.atomic
def comentar(*, chamado_id, ator, texto, interno=False, request=None):
    chamado = bloqueado(chamado_id, ator)
    dono = chamado.solicitante_id == ator.pk
    if interno and dono:
        raise PermissionDenied("Solicitante não pode acessar ou criar nota interna.")
    if not dono:
        exigir_atendimento(chamado, ator)
    comentario = adicionar_comentario(chamado, ator, texto, interno, timezone.now(), request)
    if dono and not interno and chamado.status == Status.AGUARDANDO_SOLICITANTE:
        sla.retomar(chamado, timezone.now())
        mudar_status(
            chamado, Status.EM_ATENDIMENTO, ator, "Resposta pública do solicitante", request
        )
    return comentario


@transaction.atomic
def reatribuir_chamado(*, chamado_id, ator, responsavel_id, request=None):
    chamado = bloqueado(chamado_id, ator)
    if ator.perfil != "GESTOR":
        raise PermissionDenied("Reatribuição exige Gestor.")
    if chamado.status == Status.RESOLVIDO:
        raise Conflito("Chamado resolvido não aceita reatribuição.")
    responsavel = Usuario.objects.filter(
        pk=responsavel_id, perfil="ANALISTA", is_active=True, nivel=chamado.nivel_atual
    ).first()
    if responsavel is None:
        raise ValidationError({"responsavel": "Informe Analista ativo do mesmo nível."})
    antes = snapshot(chamado)
    chamado.responsavel = responsavel
    if chamado.status in (Status.ABERTO, Status.REABERTO):
        mudar_status(
            chamado,
            Status.EM_ATENDIMENTO,
            ator,
            "Gestor atribuiu atendimento",
            request,
            antes=antes,
        )
    else:
        chamado.save(update_fields=["responsavel"])
    auditar(chamado, ator, "CHAMADO_REATRIBUIDO", request, antes=antes)
    return chamado


@transaction.atomic
def fechar_por_prazo(chamado_id, agora):
    chamado = Chamado.objects.select_for_update().get(pk=chamado_id)
    if not elegivel_fechamento(chamado, agora):
        return False
    chamado.fechado_em = agora
    mudar_status(
        chamado, Status.FECHADO, None, "Fechamento automático após 48h sem interação do solicitante"
    )
    return True
