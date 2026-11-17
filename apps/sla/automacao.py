from datetime import timedelta

from django.db import transaction
from django.db.models import Prefetch, prefetch_related_objects
from django.utils import timezone

from apps.auditoria.services import registrar_evento
from apps.chamados.choices import Status
from apps.chamados.models import Chamado
from apps.chamados.services import elegivel_fechamento, fechar_por_prazo
from apps.chamados.services_escalonamento import ATIVOS, escalar_bloqueado

from .indicadores import ciclos_com_pausa, indicadores
from .models import AlertaSLA
from .services import registrar_violacao


@transaction.atomic
def processar(chamado_id, agora):
    resultado = {"alertas": 0, "escalados": 0, "fechados": 0}
    chamado = Chamado.objects.select_for_update().get(pk=chamado_id)
    if elegivel_fechamento(chamado, agora):
        resultado["fechados"] = int(fechar_por_prazo(chamado_id, agora))
        return resultado
    if chamado.status not in ATIVOS:
        return resultado
    prefetch_related_objects([chamado], Prefetch("ciclos", queryset=ciclos_com_pausa()))
    ciclos = list(chamado.ciclos.all())
    ciclo = ciclos[-1]
    registrar_violacao(ciclo, agora)
    dados = indicadores(chamado, agora)
    risco = dados["resolucao"]["status"] in ("EM_RISCO", "VENCIDO")
    critico = (
        chamado.prioridade == "CRITICA"
        and chamado.responsavel_id is None
        and agora >= chamado.aberto_em + timedelta(minutes=10)
    )
    primeira = dados["primeira_resposta"]["status"] in ("EM_RISCO", "VENCIDO")
    gatilhos = []
    if risco:
        gatilhos.append("RESOLUCAO_EM_RISCO")
    if critico:
        gatilhos.append("CRITICO_SEM_RESPONSAVEL")
    if primeira:
        gatilhos.append("PRIMEIRA_RESPOSTA_EM_RISCO")
    for tipo in gatilhos:
        alerta, criado = AlertaSLA.objects.get_or_create(
            chamado=chamado,
            ciclo=ciclo,
            tipo=tipo,
            defaults={"triagem_pendente": chamado.triado_em is None},
        )
        if criado:
            registrar_evento(
                acao="ALERTA_SLA_CRIADO",
                entidade="chamado",
                entidade_id=chamado.pk,
                depois={"alerta_id": alerta.pk, "tipo": tipo},
            )
            resultado["alertas"] += 1
    if chamado.nivel_atual == "N1" and chamado.triado_em is not None and (risco or critico):
        escalar_bloqueado(
            chamado,
            ator=None,
            motivo="RESOLUCAO_EM_RISCO" if risco else "CRITICO_SEM_RESPONSAVEL",
            automatico=True,
        )
        resultado["escalados"] = 1
    return resultado


def verificar_sla(agora=None):
    agora = agora or timezone.now()
    total = {"alertas": 0, "escalados": 0, "fechados": 0}
    ids = Chamado.objects.exclude(status__in=[Status.FECHADO, Status.CANCELADO]).values_list(
        "pk", flat=True
    )
    for chamado_id in ids.iterator(chunk_size=200):
        resultado = processar(chamado_id, agora)
        for key in total:
            total[key] += resultado[key]
    return total
