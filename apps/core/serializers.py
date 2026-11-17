from rest_framework import serializers


class ErroDetalheSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.JSONField()


class ErroSerializer(serializers.Serializer):
    error = ErroDetalheSerializer()
