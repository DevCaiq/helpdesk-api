import pytest
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction

pytestmark = pytest.mark.django_db


def test_usuario_autentica_com_email_sem_username():
    user = get_user_model().objects.create_user("Pessoa@Example.COM", "Senha-forte-123")
    assert user.email == "pessoa@example.com"
    assert user.check_password("Senha-forte-123")
    assert "username" not in {field.name for field in user._meta.fields}
    assert authenticate(email="pessoa@example.com", password="Senha-forte-123") == user


def test_usuario_exige_email():
    with pytest.raises(ValueError, match="mail"):
        get_user_model().objects.create_user("", "Senha-forte-123")


def test_email_unico_independente_de_capitalizacao():
    model = get_user_model()
    model.objects.create_user("pessoa@example.com", "Senha-forte-123")
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(email="PESSOA@example.com", password="unusable")


@pytest.mark.parametrize(
    "perfil,nivel",
    [
        ("ANALISTA", None),
        ("ANALISTA", "N3"),
        ("SOLICITANTE", "N1"),
        ("GESTOR", "N2"),
        ("INVALIDO", None),
    ],
)
def test_banco_rejeita_perfil_nivel_invalidos(perfil, nivel):
    with pytest.raises(IntegrityError), transaction.atomic():
        get_user_model().objects.create(email="pessoa@example.com", perfil=perfil, nivel=nivel)


@pytest.mark.parametrize("nivel", ["N1", "N2"])
def test_cria_analista_valido(nivel):
    user = get_user_model().objects.create_user(
        "analista@example.com", "Senha-forte-123", perfil="ANALISTA", nivel=nivel
    )
    assert user.nivel == nivel
    assert not user.is_staff


def test_cria_superusuario():
    user = get_user_model().objects.create_superuser("admin@example.com", "Senha-forte-123")
    assert user.is_staff and user.is_superuser and user.is_active
    assert user.perfil == "GESTOR"
    assert user.check_password("Senha-forte-123")


@pytest.mark.parametrize("flags", [{"is_staff": False}, {"is_superuser": False}])
def test_superusuario_rejeita_flags_invalidas(flags):
    with pytest.raises(ValueError):
        get_user_model().objects.create_superuser("admin@example.com", "Senha-forte-123", **flags)


def test_superusuario_exige_senha():
    with pytest.raises(ValueError, match="senha"):
        get_user_model().objects.create_superuser("admin@example.com", None)
