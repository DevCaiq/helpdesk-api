import time

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle


@pytest.fixture(autouse=True)
def clear_throttles(monkeypatch):
    # Resolve o relógio dinamicamente, inclusive quando freezegun o substitui.
    monkeypatch.setattr(SimpleRateThrottle, "timer", staticmethod(lambda: time.time()))
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def usuario_factory(db):
    def create(perfil="SOLICITANTE", **kwargs):
        email = kwargs.pop("email", f"user{get_user_model().objects.count()}@example.com")
        return get_user_model().objects.create_user(
            email, "Senha-segura!12345", perfil=perfil, **kwargs
        )

    return create


@pytest.fixture
def equipe(usuario_factory):
    return {
        "dono": usuario_factory(),
        "outro": usuario_factory(),
        "n1": usuario_factory(perfil="ANALISTA", nivel="N1"),
        "n1b": usuario_factory(perfil="ANALISTA", nivel="N1"),
        "n2": usuario_factory(perfil="ANALISTA", nivel="N2"),
        "gestor": usuario_factory(perfil="GESTOR"),
    }


@pytest.fixture
def categoria(api, equipe):
    api.force_authenticate(equipe["gestor"])
    response = api.post("/api/v1/categorias/", {"nome": "Infraestrutura"}, format="json")
    assert response.status_code == 201
    return response.data["id"]


@pytest.fixture
def abrir(api, equipe, categoria):
    def create(ator=None, **extra):
        api.force_authenticate(ator or equipe["dono"])
        response = api.post(
            "/api/v1/chamados/",
            {
                "titulo": "Sem acesso",
                "descricao": "Falha no acesso ao sistema",
                "categoria": categoria,
                "impacto": "MEDIO",
                "urgencia": "MEDIA",
                **extra,
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        return response.data

    return create
