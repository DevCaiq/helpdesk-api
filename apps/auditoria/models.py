from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ImutavelQuerySet(models.QuerySet):
    def bulk_create(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ):
        if update_conflicts:
            raise ValidationError("Auditoria não permite atualização por conflito.")
        return super().bulk_create(
            objs,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=False,
            update_fields=update_fields,
            unique_fields=unique_fields,
        )

    def update(self, **kwargs):
        raise ValidationError("Auditoria não permite alterações.")

    def delete(self):
        raise ValidationError("Auditoria não permite exclusões.")


class LogAuditoria(models.Model):
    ator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True
    )
    acao = models.CharField(max_length=60, db_index=True)
    entidade = models.CharField(max_length=60, default="usuario")
    entidade_id = models.CharField(max_length=50, blank=True)
    antes = models.JSONField(default=dict)
    depois = models.JSONField(default=dict)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    objects = ImutavelQuerySet.as_manager()

    class Meta:
        ordering = ["-criado_em", "-id"]

    def save(self, *args, **kwargs):
        if not self._state.adding or self.pk is not None:
            raise ValidationError("Auditoria não permite alterações.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Auditoria não permite exclusões.")
