import uuid

from django.db import models
from django.utils import timezone


class DemoDataset(models.Model):
    chave = models.CharField(max_length=40, unique=True)
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    referencia = models.DateTimeField(default=timezone.now)
    dados = models.JSONField(default=dict)
