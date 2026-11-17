from datetime import datetime

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from apps.usuarios.serializers import StrictSerializer


class DataHoraComFuso(serializers.DateTimeField):
    def to_internal_value(self, data):
        original = data
        if isinstance(data, str):
            try:
                original = parse_datetime(data)
            except ValueError:
                original = None
        if isinstance(original, datetime) and timezone.is_naive(original):
            raise serializers.ValidationError("Informe data e hora ISO8601 com fuso ou Z.")
        return super().to_internal_value(data)


class PeriodoSerializer(StrictSerializer):
    inicio = DataHoraComFuso(required=False, help_text="Início inclusivo, ISO8601 com fuso ou Z.")
    fim = DataHoraComFuso(required=False, help_text="Fim exclusivo, ISO8601 com fuso ou Z.")

    def validate(self, attrs):
        inicio, fim = attrs.get("inicio"), attrs.get("fim")
        if inicio is not None and fim is not None and fim <= inicio:
            raise serializers.ValidationError({"fim": "Deve ser posterior ao início."})
        return attrs


def aplicar_periodo(queryset, campo, *, inicio=None, fim=None):
    if inicio is not None:
        queryset = queryset.filter(**{f"{campo}__gte": inicio})
    if fim is not None:
        queryset = queryset.filter(**{f"{campo}__lt": fim})
    return queryset
