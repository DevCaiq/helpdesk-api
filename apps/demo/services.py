import json
import os
import secrets
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import Q

from apps.auditoria.services import registrar_evento
from apps.chamados.models import Categoria, Chamado
from apps.usuarios.models import Usuario
from apps.usuarios.services import criar_usuario

from .cenarios import criar_cenarios
from .exportacao import exportar_ambiente, gravar_atomico
from .models import DemoDataset

CONTAS = {
    "gestor": ("GESTOR", None),
    "solicitante": ("SOLICITANTE", None),
    "outro": ("SOLICITANTE", None),
    "n1": ("ANALISTA", "N1"),
    "n2": ("ANALISTA", "N2"),
}


def email_demo(papel):
    return f"{papel}@demo.helpdesk.example"


def novas_senhas(contas):
    senhas = {}
    for papel, usuario in contas.items():
        senha = os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(24)
        try:
            validate_password(senha, usuario)
        except ValidationError as exc:
            raise CommandError("DEMO_PASSWORD não atende aos validadores de senha.") from exc
        senhas[papel] = senha
    return senhas


def contas_do_manifesto(manifesto):
    dados = manifesto.dados
    try:
        if set(dados["usuarios"]) != set(CONTAS):
            raise ValueError
        contas = {
            papel: Usuario.objects.get(pk=pk, email=email_demo(papel))
            for papel, pk in dados["usuarios"].items()
        }
        cat_ids = list(dados["categorias"].values())
        ticket_ids = list(dados["chamados"].values())
        if len(cat_ids) != 2 or Categoria.objects.filter(pk__in=cat_ids).count() != 2:
            raise ValueError
        if (
            len(ticket_ids) != 11
            or Chamado.objects.filter(
                pk__in=ticket_ids,
                solicitante_id__in=[u.pk for u in contas.values()],
                categoria_id__in=cat_ids,
            ).count()
            != 11
        ):
            raise ValueError
        return contas
    except (KeyError, ValueError, TypeError, Usuario.DoesNotExist) as exc:
        raise CommandError("Manifesto demo inconsistente; nenhuma conta foi alterada.") from exc


def verificar_artefato(path, uid):
    if not path.is_file() or path.is_symlink():
        raise CommandError("Ambiente privado ausente. Use --rotacionar-senhas para reexportar.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        values = {v["key"]: v["value"] for v in payload["values"]}
        if values.get("demo_uid") != str(uid):
            raise ValueError
    except (ValueError, KeyError, TypeError) as exc:
        raise CommandError("Artefato não pertence a este demo; não será sobrescrito.") from exc


def criar_contas(referencia):
    from freezegun import freeze_time

    prototipos = {
        p: Usuario(email=email_demo(p), nome=f"Demo {p}", perfil=perfil, nivel=nivel)
        for p, (perfil, nivel) in CONTAS.items()
    }
    senhas = novas_senhas(prototipos)
    contas = {}
    with freeze_time(referencia - timedelta(days=7)):
        for papel, (perfil, nivel) in CONTAS.items():
            dados = {
                "email": email_demo(papel),
                "nome": f"Demo {papel}",
                "perfil": perfil,
                "nivel": nivel,
                "password": senhas[papel],
                "date_joined": referencia - timedelta(days=7),
            }
            if papel == "gestor":
                usuario = Usuario.objects.create_user(**dados)
                registrar_evento(
                    acao="DEMO_GESTOR_CRIADO",
                    ator=usuario,
                    entidade_id=usuario.pk,
                    depois={"perfil": perfil},
                )
            else:
                usuario = criar_usuario(dados=dados, ator=contas["gestor"])
            contas[papel] = usuario
    return contas, senhas


def seed_demo(*, ambiente, rotacionar=False):
    if not getattr(settings, "ALLOW_DEMO_SEED", False):
        raise CommandError("Seed de demonstração desabilitado neste ambiente.")
    path = Path(ambiente).absolute()
    if not path.name.endswith(".postman_environment.json") or path.name.lower().endswith(
        ".example.postman_environment.json"
    ):
        raise CommandError("Use nome privado terminado em .postman_environment.json, sem .example.")
    if path.is_symlink() or path.parent.is_symlink():
        raise CommandError("Ambiente não pode usar caminho simbólico.")
    anterior = None
    tentou_exportar = False
    try:
        with transaction.atomic():
            manifesto, criado = DemoDataset.objects.select_for_update().get_or_create(
                chave="portfolio-v1"
            )
            if criado:
                if path.exists():
                    raise CommandError("Destino já existe; não será sobrescrito.")
                emails = Q()
                for papel in CONTAS:
                    emails |= Q(email__iexact=email_demo(papel))
                categorias = Q(nome__iexact="Demo - Acesso") | Q(
                    nome__iexact="Demo - Infraestrutura"
                )
                if (
                    Usuario.objects.filter(emails).exists()
                    or Categoria.objects.filter(categorias).exists()
                ):
                    raise CommandError("Colisão com contas/categorias existentes; seed abortado.")
                contas, senhas = criar_contas(manifesto.referencia)
                manifesto.dados = {
                    "usuarios": {p: u.pk for p, u in contas.items()},
                    **criar_cenarios(contas, manifesto.referencia),
                }
                manifesto.save(update_fields=["dados"])
            else:
                contas = contas_do_manifesto(manifesto)
                if path.exists():
                    verificar_artefato(path, manifesto.uid)
                    if not rotacionar:
                        return {
                            "criado": False,
                            "uid": str(manifesto.uid),
                            "dados": manifesto.dados,
                            "ambiente": str(path),
                        }
                    anterior = path.read_bytes()
                elif not rotacionar:
                    raise CommandError(
                        "Ambiente privado ausente; use --rotacionar-senhas para reexportar."
                    )
                if any(u.is_staff or u.is_superuser for u in contas.values()):
                    raise CommandError(
                        "Rotação recusada: conta demo recebeu privilégios administrativos."
                    )
                senhas = novas_senhas(contas)
                for usuario in contas.values():
                    papel = next(p for p, u in contas.items() if u.pk == usuario.pk)
                    usuario.set_password(senhas[papel])
                    usuario.save(update_fields=["password"])
                    registrar_evento(
                        acao="DEMO_SENHA_ROTACIONADA",
                        ator=contas["gestor"],
                        entidade_id=usuario.pk,
                        depois={"perfil": usuario.perfil},
                    )
            tentou_exportar = True
            exportar_ambiente(
                path,
                manifesto=manifesto,
                contas=contas,
                senhas=senhas,
                substituir=anterior is not None,
            )
            resultado = {
                "criado": criado,
                "uid": str(manifesto.uid),
                "dados": manifesto.dados,
                "ambiente": str(path),
            }
        return resultado
    except BaseException:
        if tentou_exportar and path.exists():
            try:
                verificar_artefato(path, manifesto.uid)
                proprio = True
            except CommandError:
                proprio = False
            if proprio:
                if anterior is None:
                    path.unlink(missing_ok=True)
                else:
                    gravar_atomico(path, anterior, substituir=True)
        raise
