from datetime import timedelta

from django.db.models import (
    Case,
    CharField,
    DateTimeField,
    DurationField,
    ExpressionWrapper,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Cast

from .indicadores import ciclos_com_pausa


def com_status_sla(qs, agora):
    ciclo = ciclos_com_pausa().filter(chamado_id=OuterRef("pk")).order_by("-pk")
    qs = (
        qs.annotate(
            _sla_prazo=Subquery(ciclo.values("prazo")[:1]),
            _sla_minutos=Subquery(ciclo.values("minutos_aplicados")[:1]),
            _sla_pausa=Subquery(ciclo.values("pausa_aberta_inicio")[:1]),
            _sla_resultado=Subquery(ciclo.values("resultado")[:1]),
            _sla_violado=Subquery(ciclo.values("violado_em")[:1]),
        )
        .annotate(
            _sla_pausado=Case(
                When(_sla_pausa__isnull=False, then=Value(agora) - F("_sla_pausa")),
                default=Value(timedelta()),
                output_field=DurationField(),
            ),
        )
        .annotate(
            _sla_prazo_efetivo=ExpressionWrapper(
                F("_sla_prazo") + F("_sla_pausado"), output_field=DateTimeField()
            ),
        )
        .annotate(
            _sla_risco=ExpressionWrapper(
                F("_sla_prazo_efetivo")
                - ExpressionWrapper(
                    Cast(F("_sla_minutos"), IntegerField()) * Value(timedelta(seconds=12)),
                    output_field=DurationField(),
                ),
                output_field=DateTimeField(),
            ),
            _sla_primeira=Case(
                When(~Q(primeira_resposta_resultado=""), then=F("primeira_resposta_resultado")),
                When(
                    primeira_resposta_em__lte=F("prazo_primeira_resposta"), then=Value("CUMPRIDO")
                ),
                When(primeira_resposta_em__isnull=False, then=Value("VIOLADO")),
                When(prazo_primeira_resposta__lt=agora, then=Value("VENCIDO")),
                When(aberto_em__lte=agora - timedelta(minutes=96), then=Value("EM_RISCO")),
                default=Value("NO_PRAZO"),
                output_field=CharField(),
            ),
        )
        .annotate(
            _sla_resolucao=Case(
                When(~Q(_sla_resultado=""), then=F("_sla_resultado")),
                When(
                    Q(_sla_violado__isnull=False) | Q(_sla_prazo_efetivo__lt=agora),
                    then=Value("VENCIDO"),
                ),
                When(_sla_risco__lte=agora, then=Value("EM_RISCO")),
                default=Value("NO_PRAZO"),
                output_field=CharField(),
            ),
        )
    )
    finais = ["CUMPRIDO", "NAO_APLICAVEL"]
    return qs.annotate(
        _sla_status=Case(
            When(Q(_sla_primeira="VIOLADO") | Q(_sla_resolucao="VIOLADO"), then=Value("VIOLADO")),
            When(Q(_sla_primeira="VENCIDO") | Q(_sla_resolucao="VENCIDO"), then=Value("VENCIDO")),
            When(
                Q(_sla_primeira="EM_RISCO") | Q(_sla_resolucao="EM_RISCO"), then=Value("EM_RISCO")
            ),
            When(
                Q(_sla_primeira__in=finais) & Q(_sla_resolucao__in=finais),
                then=Case(
                    When(
                        Q(_sla_primeira="CUMPRIDO") | Q(_sla_resolucao="CUMPRIDO"),
                        then=Value("CUMPRIDO"),
                    ),
                    default=Value("NAO_APLICAVEL"),
                ),
            ),
            default=Value("NO_PRAZO"),
            output_field=CharField(),
        )
    )
