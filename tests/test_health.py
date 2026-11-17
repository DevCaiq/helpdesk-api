import pytest
from django.db import OperationalError


def test_health_independe_do_banco(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_ready_verifica_banco(client):
    response = client.get("/ready/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_nao_expoe_erro_de_conexao(client, monkeypatch):
    from django.db import connection

    def unavailable(*args, **kwargs):
        raise OperationalError("password=segredo host=interno")

    monkeypatch.setattr(connection, "cursor", unavailable)
    response = client.get("/ready/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert b"segredo" not in response.content
