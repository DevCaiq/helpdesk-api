from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.auditoria.services import registrar_evento, usuario_snapshot

from .models import Usuario


def exigir_gestor(ator):
    if not ator or not ator.is_active or ator.perfil != Usuario.Perfil.GESTOR:
        raise PermissionDenied("Esta ação exige perfil Gestor.")


@transaction.atomic
def criar_usuario(*, dados, ator=None, request=None):
    dados = dict(dados)
    if ator is None:
        dados["perfil"] = Usuario.Perfil.SOLICITANTE
        dados["nivel"] = None
    else:
        exigir_gestor(ator)
    usuario = Usuario.objects.create_user(**dados)
    registrar_evento(
        acao="USUARIO_CRIADO",
        ator=ator or usuario,
        entidade_id=usuario.pk,
        depois=usuario_snapshot(usuario),
        request=request,
    )
    return usuario


@transaction.atomic
def alterar_usuario(*, usuario, dados, ator, request=None):
    exigir_gestor(ator)
    usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    if usuario.pk == ator.pk and (
        dados.get("is_active") is False or dados.get("perfil", "GESTOR") != "GESTOR"
    ):
        raise ValidationError("Gestor não pode desativar ou rebaixar a própria conta.")
    antes = usuario_snapshot(usuario)
    for key, value in dados.items():
        setattr(usuario, key, value)
    usuario.full_clean()
    usuario.save()
    registrar_evento(
        acao="USUARIO_ALTERADO",
        ator=ator,
        entidade_id=usuario.pk,
        antes=antes,
        depois=usuario_snapshot(usuario),
        request=request,
    )
    return usuario
