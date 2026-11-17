from datetime import timedelta

from django.db.models import DateTimeField, OuterRef, Subquery
from django.utils import timezone

from .models import CicloResolucao, PausaSLA

ESTADOS = ("NO_PRAZO", "EM_RISCO", "VENCIDO", "CUMPRIDO", "VIOLADO", "NAO_APLICAVEL")


def ciclos_com_pausa():
    pausa = PausaSLA.objects.filter(ciclo_id=OuterRef("pk"), fim__isnull=True).values("inicio")[:1]
    return CicloResolucao.objects.annotate(
        pausa_aberta_inicio=Subquery(pausa, output_field=DateTimeField())
    )


def pausa_aberta(ciclo):
    if hasattr(ciclo, "pausa_aberta_inicio"):
        return ciclo.pausa_aberta_inicio
    return ciclo.pausas.filter(fim__isnull=True).values_list("inicio", flat=True).first()


def prazo_efetivo(ciclo, agora):
    inicio_pausa = pausa_aberta(ciclo) if ciclo.encerrado_em is None else None
    return ciclo.prazo + (agora - inicio_pausa if inicio_pausa else timedelta())


def calcular(*, inicio, prazo, momento, minutos, resultado="", violado=False, pausado=False):
    segundos = max(0, minutos * 60 + (momento - prazo).total_seconds())
    percentual = segundos / (minutos * 60) * 100
    if resultado:
        status = resultado
    elif violado or momento > prazo:
        status = "VENCIDO"
    elif percentual >= 80:
        status = "EM_RISCO"
    else:
        status = "NO_PRAZO"
    return {
        "status": status,
        "percentual_consumido": round(percentual, 2),
        "prazo": prazo,
        "violado": violado or status in ("VENCIDO", "VIOLADO"),
        "pausado": pausado,
    }


def indicadores(chamado, agora=None):
    agora = agora or timezone.now()
    fim = chamado.primeira_resposta_finalizada_em or chamado.primeira_resposta_em
    resultado = chamado.primeira_resposta_resultado
    if not resultado and chamado.primeira_resposta_em:
        resultado = (
            "CUMPRIDO"
            if chamado.primeira_resposta_em <= chamado.prazo_primeira_resposta
            else "VIOLADO"
        )
    primeira = calcular(
        inicio=chamado.aberto_em,
        prazo=chamado.prazo_primeira_resposta,
        momento=fim or agora,
        minutos=120,
        resultado=resultado,
    )
    ciclos = list(chamado.ciclos.all())
    ciclo = ciclos[-1]
    resolucao = calcular(
        inicio=ciclo.inicio,
        prazo=prazo_efetivo(ciclo, agora),
        momento=ciclo.encerrado_em or agora,
        minutos=ciclo.minutos_aplicados,
        resultado=ciclo.resultado,
        violado=ciclo.violado_em is not None,
        pausado=ciclo.encerrado_em is None and pausa_aberta(ciclo) is not None,
    )
    estados = {primeira["status"], resolucao["status"]}
    if "VIOLADO" in estados:
        status = "VIOLADO"
    elif "VENCIDO" in estados:
        status = "VENCIDO"
    elif "EM_RISCO" in estados:
        status = "EM_RISCO"
    elif estados <= {"CUMPRIDO", "NAO_APLICAVEL"}:
        status = "CUMPRIDO" if "CUMPRIDO" in estados else "NAO_APLICAVEL"
    else:
        status = "NO_PRAZO"
    return {"primeira_resposta": primeira, "resolucao": resolucao, "status": status}
