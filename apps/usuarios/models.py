from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from .managers import UsuarioManager


class Usuario(AbstractUser):
    class Perfil(models.TextChoices):
        SOLICITANTE = "SOLICITANTE", "Solicitante"
        ANALISTA = "ANALISTA", "Analista"
        GESTOR = "GESTOR", "Gestor"

    class Nivel(models.TextChoices):
        N1 = "N1", "Nível 1"
        N2 = "N2", "Nível 2"

    username = None
    email = models.EmailField("e-mail", unique=True)
    nome = models.CharField(max_length=150, blank=True)
    perfil = models.CharField(max_length=12, choices=Perfil, default=Perfil.SOLICITANTE)
    nivel = models.CharField(max_length=2, choices=Nivel, null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        constraints = [
            models.UniqueConstraint(Lower("email"), name="usuario_email_ci_unico"),
            models.CheckConstraint(
                condition=(
                    models.Q(perfil="ANALISTA", nivel__isnull=False, nivel__in=["N1", "N2"])
                    | models.Q(perfil__in=["SOLICITANTE", "GESTOR"], nivel__isnull=True)
                ),
                name="usuario_perfil_nivel_valido",
            ),
        ]

    def clean(self):
        super().clean()
        self.email = type(self).objects.normalize_email(self.email)

    def __str__(self):
        return self.email
