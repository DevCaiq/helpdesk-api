from datetime import timedelta

import pytest
from django.apps import apps
from django.utils import timezone
from freezegun import freeze_time

from tests.helpers import action, resolver

pytestmark = pytest.mark.django_db
VOLUME = "/api/v1/metricas/volume/"
SLA = "/api/v1/metricas/sla/"


@pytest.mark.parametrize("url", [VOLUME, SLA])
@pytest.mark.parametrize(
    "papel,status", [(None, 401), ("dono", 403), ("n1", 403), ("n2", 403), ("gestor", 200)]
)
def test_acesso_metricas(api, equipe, url, papel, status):
    if papel:
        api.force_authenticate(equipe[papel])
    assert api.get(url).status_code == status


def test_metricas_vazias_sem_taxa_artificial(api, equipe):
    api.force_authenticate(equipe["gestor"])
    volume = api.get(VOLUME)
    assert volume.status_code == 200
    assert volume.data["total"] == 0
    assert len(volume.data["por_status"]) == 7
    assert all(x["total"] == 0 for x in volume.data["por_status"])
    assert volume.data["por_categoria"] == []
    dados = api.get(SLA)
    assert dados.status_code == 200
    for key in ("primeira_resposta", "resolucao"):
        assert dados.data[key]["denominador"] == 0
        assert dados.data[key]["taxa_cumprimento_percentual"] is None


def test_volume_agrupa_estado_atual_sem_duplicar_ciclos(api, equipe, abrir, categoria):
    um = abrir()
    resolver(api, equipe, um)
    action(api, equipe, um, "reabrir", {"motivo": "Falha voltou"}, papel="dono")
    dois = abrir(impacto="ALTO", urgencia="ALTA")
    action(api, equipe, dois, "assumir")
    api.force_authenticate(equipe["gestor"])
    response = api.get(VOLUME)
    assert response.data["total"] == 2
    por_status = {x["status"]: x["total"] for x in response.data["por_status"]}
    assert por_status["REABERTO"] == 1 and por_status["EM_ATENDIMENTO"] == 1
    assert response.data["por_categoria"] == [
        {"categoria_id": categoria, "nome": "Infraestrutura", "total": 2}
    ]
    assert response.data["por_nivel"] == [{"nivel": "N1", "total": 2}, {"nivel": "N2", "total": 0}]


def test_sla_conta_ciclos_reabertos_sem_recontar_primeira_resposta(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
        resolver(api, equipe, chamado)
        action(api, equipe, chamado, "reabrir", {"motivo": "Falha retornou"}, papel="dono")
        action(api, equipe, chamado, "assumir")
        cancelado = abrir()
        action(
            api,
            equipe,
            cancelado,
            "transicionar",
            {"status": "CANCELADO", "motivo": "Desisti"},
            papel="dono",
        )
        abrir()  # Pendente não entra no denominador.
    with freeze_time(inicio + timedelta(hours=5)):
        action(
            api, equipe, chamado, "transicionar", {"status": "RESOLVIDO", "motivo": "Solução final"}
        )
    api.force_authenticate(equipe["gestor"])
    response = api.get(SLA)
    assert response.status_code == 200
    primeira = response.data["primeira_resposta"]
    assert primeira["cumpridos"] == 1 and primeira["violados"] == 0
    assert primeira["nao_aplicaveis"] == 1 and primeira["denominador"] == 1
    assert primeira["taxa_cumprimento_percentual"] == 100.0
    resolucao = response.data["resolucao"]
    assert resolucao["cumpridos"] == 1 and resolucao["violados"] == 1
    assert resolucao["nao_aplicaveis"] == 1 and resolucao["total_concluidos"] == 3
    assert resolucao["numerador"] == 1 and resolucao["denominador"] == 2
    assert resolucao["taxa_cumprimento_percentual"] == 50.0


def test_periodo_sla_usa_conclusao_e_volume_usa_abertura(api, equipe, abrir):
    with freeze_time("2026-11-01T12:00:00Z"):
        chamado = abrir()
        action(api, equipe, chamado, "assumir")
    with freeze_time("2026-11-02T12:00:00Z"):
        action(api, equipe, chamado, "transicionar", {"status": "RESOLVIDO", "motivo": "Solução"})
    params = {"inicio": "2026-11-02T00:00:00Z", "fim": "2026-11-03T00:00:00Z"}
    api.force_authenticate(equipe["gestor"])
    assert api.get(VOLUME, params).data["total"] == 0
    response = api.get(SLA, params)
    assert response.data["primeira_resposta"]["violados"] == 1
    assert response.data["resolucao"]["cumpridos"] == 1  # Exatamente no prazo de 24h.


def test_periodo_inclui_inicio_exclui_fim_e_normaliza_fuso(api, equipe, abrir):
    with freeze_time("2026-11-02T03:00:00Z"):
        abrir()
    with freeze_time("2026-11-03T03:00:00Z"):
        abrir()
    api.force_authenticate(equipe["gestor"])
    response = api.get(
        VOLUME, {"inicio": "2026-11-02T00:00:00-03:00", "fim": "2026-11-03T00:00:00-03:00"}
    )
    assert response.status_code == 200 and response.data["total"] == 1


@pytest.mark.parametrize(
    "params",
    [
        {"inicio": "ontem"},
        {"inicio": "2026-02-30T00:00:00Z"},
        {"inicio": "2026-11-02"},
        {"inicio": "2026-11-02T00:00:00"},
        {"inicio": "2026-11-03T00:00:00Z", "fim": "2026-11-02T00:00:00Z"},
        {"inicio": "2026-11-02T00:00:00Z", "fim": "2026-11-02T00:00:00Z"},
        {"inexistente": "campo"},
    ],
)
@pytest.mark.parametrize("url", [VOLUME, SLA])
def test_metricas_rejeitam_periodos_invalidos(api, equipe, params, url):
    api.force_authenticate(equipe["gestor"])
    response = api.get(url, params)
    assert response.status_code == 400
    assert response.data["error"]["code"] == "dados_invalidos"


def test_agregacoes_nao_carregam_chamado_por_chamado(api, equipe, abrir, django_assert_num_queries):
    for _ in range(4):
        resolver(api, equipe, abrir())
    api.force_authenticate(equipe["gestor"])
    for url in (VOLUME, SLA):
        with django_assert_num_queries(2):
            response = api.get(url)
        assert response.status_code == 200


def test_leituras_nao_geram_auditoria(api, equipe, abrir):
    abrir()
    model = apps.get_model("auditoria", "LogAuditoria")
    antes = model.objects.count()
    api.force_authenticate(equipe["gestor"])
    api.get(VOLUME)
    api.get(SLA)
    assert model.objects.count() == antes


@pytest.mark.parametrize("url", [VOLUME, SLA, "/api/v1/auditoria/"])
def test_flags_admin_nao_substituem_perfil_gestor(api, usuario_factory, url):
    usuario = usuario_factory(is_staff=True, is_superuser=True)
    api.force_authenticate(usuario)
    assert api.get(url).status_code == 403


@pytest.mark.parametrize(
    "mudanca,status", [({"perfil": "SOLICITANTE"}, 403), ({"is_active": False}, 401)]
)
def test_token_existente_nao_ignora_revogacao_perfil_ou_desativacao(api, equipe, mudanca, status):
    from rest_framework_simplejwt.tokens import RefreshToken

    user = equipe["gestor"]
    token = str(RefreshToken.for_user(user).access_token)
    apps.get_model("usuarios", "Usuario").objects.filter(pk=user.pk).update(**mudanca)
    api.credentials(HTTP_AUTHORIZATION="Bearer " + token)
    for url in (VOLUME, SLA, "/api/v1/auditoria/"):
        assert api.get(url).status_code == status


def test_sla_arredonda_percentual_sem_contar_pendentes(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamados = [abrir() for _ in range(3)]
        for chamado in chamados:
            action(api, equipe, chamado, "assumir")
    with freeze_time(inicio + timedelta(hours=1)):
        action(api, equipe, chamados[0], "comentarios", {"texto": "Em análise"})
    with freeze_time(inicio + timedelta(hours=3)):
        for chamado in chamados[1:]:
            action(api, equipe, chamado, "comentarios", {"texto": "Em análise"})
    api.force_authenticate(equipe["gestor"])
    dados = api.get(SLA).data
    assert dados["primeira_resposta"]["denominador"] == 3
    assert dados["primeira_resposta"]["taxa_cumprimento_percentual"] == 33.33
    assert dados["resolucao"]["denominador"] == 0
    assert dados["resolucao"]["taxa_cumprimento_percentual"] is None


def test_periodo_com_apenas_um_limite(api, equipe, abrir):
    with freeze_time("2026-11-02T12:00:00Z"):
        abrir()
    api.force_authenticate(equipe["gestor"])
    assert api.get(VOLUME, {"inicio": "2026-11-02T00:00:00Z"}).data["total"] == 1
    assert api.get(VOLUME, {"fim": "2026-11-02T00:00:00Z"}).data["total"] == 0
