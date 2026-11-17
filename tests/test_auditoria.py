import json

import pytest
from django.apps import apps
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.django_db


def test_login_audita_sucesso_e_falha_sem_segredos(api, usuario_factory):
    user = usuario_factory()
    for password in ["Senha-segura!12345", "senha-incorreta"]:
        api.post("/api/v1/auth/login/", {"email": user.email, "password": password}, format="json")
    model = apps.get_model("auditoria", "LogAuditoria")
    assert model.objects.filter(acao="LOGIN_SUCESSO", ator=user).count() == 1
    assert model.objects.filter(acao="LOGIN_FALHA", ator=None).count() == 1
    payload = json.dumps(list(model.objects.values("antes", "depois")))
    assert "password" not in payload and "Senha-segura" not in payload and "refresh" not in payload


def test_cadastro_e_alteracao_auditados(api, usuario_factory):
    model = apps.get_model("auditoria", "LogAuditoria")
    gestor = usuario_factory(perfil="GESTOR")
    response = api.post(
        "/api/v1/usuarios/",
        {
            "email": "pessoa@example.com",
            "nome": "Pessoa",
            "password": "Senha-segura!12345",
        },
        format="json",
    )
    assert response.status_code == 201
    user_id = response.data["id"]
    assert model.objects.filter(acao="USUARIO_CRIADO", entidade_id=str(user_id)).exists()
    api.force_authenticate(gestor)
    assert (
        api.patch(f"/api/v1/usuarios/{user_id}/", {"nome": "Outro"}, format="json").status_code
        == 200
    )
    event = model.objects.get(acao="USUARIO_ALTERADO")
    assert event.antes["nome"] == "Pessoa" and event.depois["nome"] == "Outro"
    assert event.ator == gestor


def test_auditoria_append_only(usuario_factory):
    model = apps.get_model("auditoria", "LogAuditoria")
    event = model.objects.create(acao="TESTE", ator=usuario_factory())
    with pytest.raises(ValidationError):
        event.save()
    with pytest.raises(ValidationError):
        event.delete()
    with pytest.raises(ValidationError):
        model.objects.filter(pk=event.pk).update(acao="ALTERADO")
    with pytest.raises(ValidationError):
        model.objects.filter(pk=event.pk).delete()
    with pytest.raises(ValidationError):
        model(pk=event.pk, acao="SUBSTITUIDO").save()


def test_falha_auditoria_reverte_cadastro(api, monkeypatch):
    from django.contrib.auth import get_user_model

    from apps.usuarios import services

    def falha(**kwargs):
        raise RuntimeError("falha de auditoria")

    monkeypatch.setattr(services, "registrar_evento", falha)
    with pytest.raises(RuntimeError, match="auditoria"):
        api.post(
            "/api/v1/usuarios/",
            {
                "email": "pessoa@example.com",
                "nome": "Pessoa",
                "password": "Senha-segura!12345",
            },
            format="json",
        )
    assert not get_user_model().objects.exists()


def test_upsert_nao_pode_alterar_auditoria():
    model = apps.get_model("auditoria", "LogAuditoria")
    event = model.objects.create(acao="ORIGINAL")
    with pytest.raises(ValidationError):
        model.objects.bulk_create(
            [model(pk=event.pk, acao="ALTERADO")],
            update_conflicts=True,
            unique_fields=["id"],
            update_fields=["acao"],
        )
    event.refresh_from_db()
    assert event.acao == "ORIGINAL"
