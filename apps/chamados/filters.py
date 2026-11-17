from django.utils import timezone
from django_filters import rest_framework as filters

from apps.sla.filters import com_status_sla
from apps.sla.indicadores import ESTADOS

from .models import Chamado


class ChamadoFilter(filters.FilterSet):
    sla_status = filters.ChoiceFilter(choices=[(x, x) for x in ESTADOS], method="filtrar_sla")
    aberto_em_de = filters.IsoDateTimeFilter(field_name="aberto_em", lookup_expr="gte")
    aberto_em_ate = filters.IsoDateTimeFilter(field_name="aberto_em", lookup_expr="lte")

    def filtrar_sla(self, queryset, name, value):
        return com_status_sla(queryset, timezone.now()).filter(_sla_status=value)

    class Meta:
        model = Chamado
        fields = ("status", "prioridade", "categoria", "responsavel", "solicitante", "nivel_atual")
