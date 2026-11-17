from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

pytestmark = pytest.mark.django_db
AUTH = "/api/v1/auth/"


def login(api, user, password="Senha-segura!12345"):
    return api.post(
        AUTH + "login/", {"email": user.email.upper(), "password": password}, format="json"
    )


def test_login_emite_tokens_com_prazos_corretos(api, usuario_factory):
    response = login(api, usuario_factory())
    assert response.status_code == 200
    access = AccessToken(response.data["access"])
    refresh = RefreshToken(response.data["refresh"])
    assert access["exp"] - access["iat"] == 15 * 60
    assert refresh["exp"] - refresh["iat"] == 7 * 86400
    api.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
    assert api.get("/api/v1/usuarios/me/").status_code == 200


def test_refresh_rotaciona_e_bloqueia_reutilizacao(api, usuario_factory):
    tokens = login(api, usuario_factory()).data
    response = api.post(AUTH + "refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert response.status_code == 200
    assert response.data["refresh"] != tokens["refresh"]
    assert (
        api.post(AUTH + "refresh/", {"refresh": tokens["refresh"]}, format="json").status_code
        == 401
    )


def test_logout_revoga_refresh_proprio(api, usuario_factory):
    tokens = login(api, usuario_factory()).data
    api.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    assert (
        api.post(AUTH + "logout/", {"refresh": tokens["refresh"]}, format="json").status_code == 204
    )
    assert (
        api.post(AUTH + "refresh/", {"refresh": tokens["refresh"]}, format="json").status_code
        == 401
    )
    assert api.get("/api/v1/usuarios/me/").status_code == 200


def test_logout_nao_revoga_token_de_outro(api, usuario_factory):
    primeiro, segundo = usuario_factory(), usuario_factory()
    tokens = login(api, primeiro).data
    outro = login(api, segundo).data
    api.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    assert (
        api.post(AUTH + "logout/", {"refresh": outro["refresh"]}, format="json").status_code == 403
    )
    assert (
        api.post(AUTH + "refresh/", {"refresh": outro["refresh"]}, format="json").status_code == 200
    )


def test_logout_exige_autenticacao(api, usuario_factory):
    token = str(RefreshToken.for_user(usuario_factory()))
    assert api.post(AUTH + "logout/", {"refresh": token}, format="json").status_code == 401


def test_credencial_invalida_e_conta_inativa(api, usuario_factory):
    user = usuario_factory()
    assert login(api, user, "incorreta").status_code == 401
    user.is_active = False
    user.save()
    assert login(api, user).status_code == 401


def test_desativacao_bloqueia_access_e_refresh(api, usuario_factory):
    user = usuario_factory()
    tokens = login(api, user).data
    user.is_active = False
    user.save()
    api.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    assert api.get("/api/v1/usuarios/me/").status_code == 401
    assert (
        api.post(AUTH + "refresh/", {"refresh": tokens["refresh"]}, format="json").status_code
        == 401
    )


def test_refresh_de_usuario_excluido_nao_gera_erro_500(api, usuario_factory):
    user = usuario_factory()
    tokens = {"refresh": str(RefreshToken.for_user(user))}
    user.delete()
    assert (
        api.post(AUTH + "refresh/", {"refresh": tokens["refresh"]}, format="json").status_code
        == 401
    )


@pytest.mark.parametrize("endpoint", ["refresh/", "logout/"])
def test_token_malformado(api, usuario_factory, endpoint):
    api.force_authenticate(usuario_factory())
    response = api.post(AUTH + endpoint, {"refresh": "invalido"}, format="json")
    assert response.status_code == 401
    assert "error" in response.data


def test_access_expira_em_15_minutos(api, usuario_factory):
    user = usuario_factory()
    inicio = timezone.now()
    with freeze_time(inicio):
        tokens = login(api, user).data
    with freeze_time(inicio + timedelta(minutes=15, seconds=1)):
        api.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
        assert api.get("/api/v1/usuarios/me/").status_code == 401


def test_refresh_expira_em_sete_dias(api, usuario_factory):
    user = usuario_factory()
    inicio = timezone.now()
    with freeze_time(inicio):
        tokens = login(api, user).data
    with freeze_time(inicio + timedelta(days=7, seconds=1)):
        response = api.post(AUTH + "refresh/", {"refresh": tokens["refresh"]}, format="json")
        assert response.status_code == 401


def test_mudanca_de_perfil_revoga_permissao_do_access_existente(api, usuario_factory):
    user = usuario_factory(perfil="GESTOR")
    tokens = login(api, user).data
    user.perfil = "SOLICITANTE"
    user.save()
    api.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    assert api.get("/api/v1/usuarios/").status_code == 403


def test_login_tem_limite_de_tentativas(api, usuario_factory):
    user = usuario_factory()
    responses = [login(api, user, "incorreta") for _ in range(11)]
    assert responses[0].status_code == 401
    assert responses[-1].status_code == 429
