from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.auditoria.services import registrar_evento
from apps.core.exceptions import Conflito

from .models import Categoria


@transaction.atomic
def salvar_categoria(*, ator, dados, categoria=None, request=None):
    if ator.perfil != "GESTOR" or not ator.is_active:
        raise PermissionDenied("Ação exclusiva do Gestor.")
    antes = {"nome": categoria.nome, "ativa": categoria.ativa} if categoria else {}
    categoria = categoria or Categoria()
    for key in ("nome", "ativa"):
        if key in dados:
            setattr(categoria, key, dados[key])
    categoria.full_clean()
    categoria.save()
    registrar_evento(
        acao="CATEGORIA_ALTERADA" if antes else "CATEGORIA_CRIADA",
        ator=ator,
        entidade="categoria",
        entidade_id=categoria.pk,
        antes=antes,
        depois={"nome": categoria.nome, "ativa": categoria.ativa},
        request=request,
    )
    return categoria


@transaction.atomic
def excluir_categoria(*, ator, categoria, request=None):
    if ator.perfil != "GESTOR" or not ator.is_active:
        raise PermissionDenied("Ação exclusiva do Gestor.")
    if categoria.chamados.exists():
        raise Conflito("Categoria utilizada: desative em vez de excluir.")
    registrar_evento(
        acao="CATEGORIA_EXCLUIDA",
        ator=ator,
        entidade="categoria",
        entidade_id=categoria.pk,
        antes={"nome": categoria.nome, "ativa": categoria.ativa},
        request=request,
    )
    categoria.delete()
