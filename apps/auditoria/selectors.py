from apps.core.periodos import aplicar_periodo

from .models import LogAuditoria


def consultar_logs(filtros):
    qs = aplicar_periodo(
        LogAuditoria.objects.all(),
        "criado_em",
        inicio=filtros.get("inicio"),
        fim=filtros.get("fim"),
    )
    for campo in ("ator", "acao", "entidade", "entidade_id"):
        if campo in filtros:
            qs = qs.filter(**{campo: filtros[campo]})
    if "sistema" in filtros:
        qs = qs.filter(ator__isnull=filtros["sistema"])
    return qs.order_by("-criado_em", "-id")
