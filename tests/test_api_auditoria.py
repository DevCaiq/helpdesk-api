import pytest
from django.apps import apps
from freezegun import freeze_time

pytestmark = pytest.mark.django_db
BASE = "/api/v1/auditoria/"


@pytest.mark.parametrize(
    "papel,status", [(None, 401), ("dono", 403), ("n1", 403), ("n2", 403), ("gestor", 200)]
)
def test_acesso_auditoria(api, equipe, papel, status):
    if papel:
        api.force_authenticate(equipe[papel])
    assert api.get(BASE).status_code == status


def test_filtros_auditoria_e_detalhe(api, equipe):
    model = apps.get_model("auditoria", "LogAuditoria")
    with freeze_time("2026-11-01T10:00:00Z"):
        model.objects.create(acao="ANTIGO", ator=equipe["gestor"])
    with freeze_time("2026-11-02T10:00:00Z"):
        esperado = model.objects.create(
            acao="STATUS_ALTERADO",
            ator=equipe["gestor"],
            entidade="chamado",
            entidade_id="25",
            depois={"status": "EM_ATENDIMENTO"},
        )
        model.objects.create(
            acao="STATUS_ALTERADO", ator=None, entidade="chamado", entidade_id="25"
        )
    api.force_authenticate(equipe["gestor"])
    response = api.get(
        BASE,
        {
            "ator": equipe["gestor"].pk,
            "acao": "STATUS_ALTERADO",
            "entidade": "chamado",
            "entidade_id": "25",
            "inicio": "2026-11-02T00:00:00Z",
            "fim": "2026-11-03T00:00:00Z",
        },
    )
    assert response.status_code == 200
    assert [x["id"] for x in response.data["results"]] == [esperado.pk]
    detail = api.get(BASE + f"{esperado.pk}/")
    assert detail.status_code == 200 and detail.data["depois"]["status"] == "EM_ATENDIMENTO"
    assert api.get(BASE + "99999/").status_code == 404
    assert api.get(BASE, {"sistema": "true"}).data["count"] == 1


def test_auditoria_e_somente_leitura(api, equipe):
    model = apps.get_model("auditoria", "LogAuditoria")
    registro = model.objects.create(acao="TESTE")
    api.force_authenticate(equipe["gestor"])
    for method in ("post", "put", "patch", "delete"):
        for url in (BASE, BASE + f"{registro.pk}/"):
            response = getattr(api, method)(url, {"acao": "ALTERADO"}, format="json")
            assert response.status_code == 405
    registro.refresh_from_db()
    assert registro.acao == "TESTE"


def test_auditoria_paginada_ordenacao_estavel_sem_novas_gravacoes(
    api, equipe, django_assert_num_queries
):
    model = apps.get_model("auditoria", "LogAuditoria")
    with freeze_time("2026-11-02T10:00:00Z"):
        for _ in range(25):
            model.objects.create(acao="TESTE", ator=equipe["gestor"])
    api.force_authenticate(equipe["gestor"])
    with django_assert_num_queries(2):
        response = api.get(BASE, {"page_size": 10})
    assert response.status_code == 200
    assert response.data["count"] == 25 and len(response.data["results"]) == 10
    ids = [x["id"] for x in response.data["results"]]
    assert ids == sorted(ids, reverse=True)
    segundo = api.get(BASE, {"page": 2, "page_size": 10})
    assert not set(ids) & {x["id"] for x in segundo.data["results"]}
    assert model.objects.count() == 25


def test_snapshot_legado_nao_expoe_segredos(api, equipe):
    model = apps.get_model("auditoria", "LogAuditoria")
    registro = model.objects.create(
        acao="LEGADO",
        entidade="usuario",
        antes={"perfil": "ANALISTA", "password": "SEGREDO_1", "token": "SEGREDO_2"},
        depois={"perfil": "GESTOR", "nome": {"password": "SEGREDO_3"}, "refresh": "SEGREDO_4"},
    )
    api.force_authenticate(equipe["gestor"])
    response = api.get(BASE + f"{registro.pk}/")
    assert response.status_code == 200
    assert response.data["antes"] == {"perfil": "ANALISTA"}
    assert response.data["depois"] == {"perfil": "GESTOR"}
    assert "SEGREDO" not in str(response.data)
    registro.refresh_from_db()
    assert "password" in registro.antes  # Leitura não altera registro imutável.


@pytest.mark.parametrize(
    "params",
    [
        {"ator": "abc"},
        {"ator": 0},
        {"sistema": "talvez"},
        {"ator": 1, "sistema": "true"},
        {"inicio": "2026-11-02"},
        {"inicio": "2026-11-03T00:00:00Z", "fim": "2026-11-02T00:00:00Z"},
        {"desconhecido": "valor"},
    ],
)
def test_auditoria_rejeita_filtros_invalidos(api, equipe, params):
    api.force_authenticate(equipe["gestor"])
    assert api.get(BASE, params).status_code == 400


def test_auditoria_limita_pagina_e_filtra_atores_humanos(api, equipe):
    model = apps.get_model("auditoria", "LogAuditoria")
    model.objects.bulk_create([model(acao="TESTE", ator=equipe["gestor"]) for _ in range(105)])
    model.objects.create(acao="SISTEMA", ator=None)
    api.force_authenticate(equipe["gestor"])
    response = api.get(BASE, {"sistema": "false", "page_size": 1000})
    assert response.status_code == 200
    assert response.data["count"] == 105
    assert len(response.data["results"]) == 100
    assert all(x["ator"] == equipe["gestor"].pk for x in response.data["results"])


def test_snapshot_de_formato_inesperado_nao_vaza_ou_causa_erro(api, equipe):
    model = apps.get_model("auditoria", "LogAuditoria")
    registro = model.objects.create(
        acao="LEGADO", entidade="nao_mapeada", antes={"corpo": "SEGREDO"}, depois=["SEGREDO"]
    )
    api.force_authenticate(equipe["gestor"])
    response = api.get(BASE + f"{registro.pk}/")
    assert response.status_code == 200
    assert response.data["antes"] == {} and response.data["depois"] == {}


def test_detalhe_auditoria_tambem_exige_gestor(api, equipe):
    registro = apps.get_model("auditoria", "LogAuditoria").objects.create(acao="TESTE")
    api.force_authenticate(equipe["n1"])
    assert api.get(BASE + f"{registro.pk}/").status_code == 403
