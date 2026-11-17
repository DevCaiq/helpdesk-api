import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db
BASE = "/api/v1/usuarios/"


def cadastro(**extra):
    return {
        "email": "Pessoa@example.com",
        "nome": "Pessoa",
        "password": "Senha-segura!12345",
        **extra,
    }


def test_cadastro_publico(api):
    response = api.post(BASE, cadastro(), format="json")
    assert response.status_code == 201
    assert response.data["perfil"] == "SOLICITANTE"
    assert "password" not in response.data
    user = get_user_model().objects.get(pk=response.data["id"])
    assert user.email == "pessoa@example.com"
    assert user.check_password("Senha-segura!12345")
    assert not user.is_staff and not user.is_superuser


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("perfil", "GESTOR"),
        ("nivel", "N1"),
        ("is_staff", True),
        ("is_superuser", True),
        ("is_active", False),
        ("id", 100),
    ],
)
def test_cadastro_rejeita_campos_nao_permitidos(api, campo, valor):
    response = api.post(BASE, cadastro(**{campo: valor}), format="json")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "dados_invalidos"
    assert not get_user_model().objects.exists()


@pytest.mark.parametrize(
    "dados", [cadastro(password="123"), cadastro(nome=""), cadastro(email="ruim")]
)
def test_cadastro_valida_dados(api, dados):
    assert api.post(BASE, dados, format="json").status_code == 400


def test_cadastro_rejeita_email_duplicado(api, usuario_factory):
    usuario_factory(email="pessoa@example.com")
    assert api.post(BASE, cadastro(), format="json").status_code == 400


def test_me_exige_autenticacao(api):
    assert api.get(BASE + "me/").status_code == 401


def test_me_nao_expoe_segredos(api, usuario_factory):
    user = usuario_factory()
    api.force_authenticate(user)
    response = api.get(BASE + "me/")
    assert response.status_code == 200
    assert response.data["id"] == user.pk
    assert not {"password", "is_staff", "is_superuser", "user_permissions"} & response.data.keys()


@pytest.mark.parametrize(
    "perfil,nivel,status",
    [
        ("SOLICITANTE", None, 403),
        ("ANALISTA", "N1", 403),
        ("GESTOR", None, 200),
    ],
)
def test_listagem_exclusiva_gestor(api, usuario_factory, perfil, nivel, status):
    api.force_authenticate(usuario_factory(perfil=perfil, nivel=nivel))
    response = api.get(BASE)
    assert response.status_code == status
    if status == 200:
        assert response.data["count"] == 1


@pytest.mark.parametrize("perfil,nivel", [("ANALISTA", "N1"), ("ANALISTA", "N2"), ("GESTOR", None)])
def test_gestor_cria_equipe_sem_acesso_admin(api, usuario_factory, perfil, nivel):
    api.force_authenticate(usuario_factory(perfil="GESTOR"))
    response = api.post(BASE + "staff/", cadastro(perfil=perfil, nivel=nivel), format="json")
    assert response.status_code == 201
    user = get_user_model().objects.get(pk=response.data["id"])
    assert user.perfil == perfil
    assert not user.is_staff and not user.is_superuser


def test_nao_gestor_nao_cria_equipe(api, usuario_factory):
    api.force_authenticate(usuario_factory())
    assert api.post(BASE + "staff/", cadastro(perfil="GESTOR"), format="json").status_code == 403


def test_gestao_valida_nivel_e_campos(api, usuario_factory):
    api.force_authenticate(usuario_factory(perfil="GESTOR"))
    for dados in [
        cadastro(perfil="ANALISTA"),
        cadastro(perfil="GESTOR", nivel="N2"),
        cadastro(perfil="GESTOR", is_staff=True),
    ]:
        assert api.post(BASE + "staff/", dados, format="json").status_code == 400


def test_gestor_altera_perfil_nivel_e_desativa(api, usuario_factory):
    gestor = usuario_factory(perfil="GESTOR")
    alvo = usuario_factory()
    api.force_authenticate(gestor)
    response = api.patch(
        BASE + f"{alvo.pk}/",
        {"perfil": "ANALISTA", "nivel": "N2", "is_active": False},
        format="json",
    )
    assert response.status_code == 200
    alvo.refresh_from_db()
    assert (alvo.perfil, alvo.nivel, alvo.is_active) == ("ANALISTA", "N2", False)


def test_atualizacao_invalida_nao_altera_usuario(api, usuario_factory):
    api.force_authenticate(usuario_factory(perfil="GESTOR"))
    alvo = usuario_factory(perfil="ANALISTA", nivel="N1")
    assert api.patch(BASE + f"{alvo.pk}/", {"perfil": "GESTOR"}, format="json").status_code == 400
    alvo.refresh_from_db()
    assert alvo.perfil == "ANALISTA"


@pytest.mark.parametrize(
    "dados", [{"is_active": False}, {"perfil": "SOLICITANTE"}, {"is_superuser": True}]
)
def test_gestor_nao_se_desativa_ou_eleva_privilegios(api, usuario_factory, dados):
    gestor = usuario_factory(perfil="GESTOR")
    api.force_authenticate(gestor)
    assert api.patch(BASE + f"{gestor.pk}/", dados, format="json").status_code == 400


def test_solicitante_nao_altera_outro_usuario(api, usuario_factory):
    api.force_authenticate(usuario_factory())
    alvo = usuario_factory()
    assert api.patch(BASE + f"{alvo.pk}/", {"is_active": False}, format="json").status_code == 403


def test_usuario_inexistente(api, usuario_factory):
    api.force_authenticate(usuario_factory(perfil="GESTOR"))
    assert api.patch(BASE + "99999/", {"nome": "Nome"}, format="json").status_code == 404


def test_cadastro_tem_limite_proprio(api):
    for _ in range(10):
        assert api.post(BASE, cadastro(password="123"), format="json").status_code == 400
    assert api.post(BASE, cadastro(), format="json").status_code == 429


def test_paginacao_limita_tamanho(api, usuario_factory):
    api.force_authenticate(usuario_factory(perfil="GESTOR"))
    model = get_user_model()
    model.objects.bulk_create([model(email=f"pagina{i}@example.com") for i in range(105)])
    response = api.get(BASE + "?page_size=1000")
    assert response.status_code == 200
    assert response.data["count"] == 106
    assert len(response.data["results"]) == 100
