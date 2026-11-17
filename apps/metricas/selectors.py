from django.db.models import Count, Q

from apps.chamados.choices import Prioridade, Status
from apps.chamados.models import Chamado
from apps.core.periodos import aplicar_periodo
from apps.sla.models import CicloResolucao


def volume(*, inicio=None, fim=None):
    qs = aplicar_periodo(Chamado.objects.all(), "aberto_em", inicio=inicio, fim=fim)
    grupos = {"status": Status.values, "nivel_atual": ["N1", "N2"], "prioridade": Prioridade.values}
    campos = {"total": Count("pk")}
    for campo, valores in grupos.items():
        for valor in valores:
            campos[f"{campo}_{valor}"] = Count("pk", filter=Q(**{campo: valor}))
    contagens = qs.aggregate(**campos)
    categorias = (
        qs.values("categoria_id", "categoria__nome")
        .annotate(total=Count("pk"))
        .order_by("categoria_id")
    )
    return {
        "periodo": {"inicio": inicio, "fim": fim},
        "base_periodo": "abertura",
        "total": contagens["total"],
        "por_status": [{"status": x, "total": contagens[f"status_{x}"]} for x in Status.values],
        "por_nivel": [{"nivel": x, "total": contagens[f"nivel_atual_{x}"]} for x in ["N1", "N2"]],
        "por_prioridade": [
            {"prioridade": x, "total": contagens[f"prioridade_{x}"]} for x in Prioridade.values
        ],
        "por_categoria": [
            {"categoria_id": x["categoria_id"], "nome": x["categoria__nome"], "total": x["total"]}
            for x in categorias
        ],
    }


def resumo_obrigacao(qs, campo_resultado):
    dados = qs.filter(
        **{f"{campo_resultado}__in": ["CUMPRIDO", "VIOLADO", "NAO_APLICAVEL"]}
    ).aggregate(
        cumpridos=Count("pk", filter=Q(**{campo_resultado: "CUMPRIDO"})),
        violados=Count("pk", filter=Q(**{campo_resultado: "VIOLADO"})),
        nao_aplicaveis=Count("pk", filter=Q(**{campo_resultado: "NAO_APLICAVEL"})),
        total_concluidos=Count("pk"),
    )
    numerador = dados["cumpridos"]
    denominador = numerador + dados["violados"]
    return {
        **dados,
        "numerador": numerador,
        "denominador": denominador,
        "taxa_cumprimento_percentual": round(numerador / denominador * 100, 2)
        if denominador
        else None,
    }


def sla(*, inicio=None, fim=None):
    primeira = aplicar_periodo(
        Chamado.objects.filter(primeira_resposta_finalizada_em__isnull=False),
        "primeira_resposta_finalizada_em",
        inicio=inicio,
        fim=fim,
    )
    resolucao = aplicar_periodo(
        CicloResolucao.objects.filter(encerrado_em__isnull=False),
        "encerrado_em",
        inicio=inicio,
        fim=fim,
    )
    return {
        "periodo": {"inicio": inicio, "fim": fim},
        "base_periodo": "conclusao_obrigacao",
        "primeira_resposta": resumo_obrigacao(primeira, "primeira_resposta_resultado"),
        "resolucao": resumo_obrigacao(resolucao, "resultado"),
    }
