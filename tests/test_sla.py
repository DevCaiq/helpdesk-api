from datetime import timedelta

import pytest
from django.apps import apps
from django.utils import timezone
from freezegun import freeze_time

from tests.helpers import action, resolver

pytestmark = pytest.mark.django_db


def detalhe(api, equipe, chamado):
    api.force_authenticate(equipe["gestor"])
    response = api.get(f"/api/v1/chamados/{chamado['id']}/")
    assert response.status_code == 200
    return response.data


@pytest.mark.parametrize(
    "minutos,status",
    [(0, "NO_PRAZO"), (95, "NO_PRAZO"), (96, "EM_RISCO"), (120, "EM_RISCO"), (121, "VENCIDO")],
)
def test_primeira_resposta_indicador_sem_job(api, equipe, abrir, minutos, status):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir()
    with freeze_time(inicio + timedelta(minutes=minutos)):
        dados = detalhe(api, equipe, chamado)
    assert dados["sla"]["primeira_resposta"]["status"] == status
    assert dados["sla"]["primeira_resposta"]["percentual_consumido"] == pytest.approx(
        minutos / 120 * 100, abs=0.01
    )


def test_pausa_aberta_congela_consumo_de_resolucao(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
        action(api, equipe, chamado, "assumir")
    with freeze_time(inicio + timedelta(hours=1)):
        action(
            api,
            equipe,
            chamado,
            "transicionar",
            {"status": "AGUARDANDO_SOLICITANTE", "motivo": "Informe mais"},
        )
    with freeze_time(inicio + timedelta(days=3)):
        sla = detalhe(api, equipe, chamado)["sla"]
    assert sla["resolucao"]["percentual_consumido"] == 25
    assert sla["resolucao"]["pausado"] is True
    assert sla["primeira_resposta"]["status"] == "CUMPRIDO"


def test_prioridade_recalcula_sem_apagar_violacao(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
        action(api, equipe, chamado, "assumir")
    with freeze_time(inicio + timedelta(hours=5)):
        response = action(
            api,
            equipe,
            chamado,
            "prioridade",
            {"prioridade": "BAIXA", "motivo": "Impacto revisado"},
        )
        assert response.status_code == 200
        assert response.data["sla"]["resolucao"]["violado"] is True
        assert response.data["sla"]["resolucao"]["status"] == "VENCIDO"
        action(api, equipe, chamado, "transicionar", {"status": "RESOLVIDO", "motivo": "Feito"})
    obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
    ciclo = obj.ciclos.get()
    assert ciclo.prazo == inicio + timedelta(hours=72)
    assert ciclo.resultado == "VIOLADO"
    assert obj.prazo_primeira_resposta == inicio + timedelta(hours=2)


def test_prioridade_durante_pausa_nao_conta_pausa_duas_vezes(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir()
        action(api, equipe, chamado, "assumir")
    with freeze_time(inicio + timedelta(hours=1)):
        action(
            api,
            equipe,
            chamado,
            "transicionar",
            {"status": "AGUARDANDO_SOLICITANTE", "motivo": "Informar erro"},
        )
    with freeze_time(inicio + timedelta(hours=3)):
        assert (
            action(
                api,
                equipe,
                chamado,
                "prioridade",
                {"prioridade": "ALTA", "motivo": "Revisão"},
                papel="gestor",
            ).status_code
            == 200
        )
    with freeze_time(inicio + timedelta(hours=4)):
        action(api, equipe, chamado, "comentarios", {"texto": "Informação"}, papel="dono")
    obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
    assert obj.ciclos.get().prazo == inicio + timedelta(hours=11)


@pytest.mark.parametrize("papel,status", [("dono", 403), ("n1b", 403), ("gestor", 200)])
def test_prioridade_permissoes(api, equipe, abrir, papel, status):
    chamado = abrir()
    action(api, equipe, chamado, "assumir")
    assert (
        action(
            api,
            equipe,
            chamado,
            "prioridade",
            {"prioridade": "ALTA", "motivo": "Revisão"},
            papel=papel,
        ).status_code
        == status
    )


def test_politicas_apenas_gestor_e_apenas_novos_chamados(api, equipe, abrir):
    antigo = abrir()
    api.force_authenticate(equipe["dono"])
    assert api.get("/api/v1/sla/politicas/").status_code == 403
    api.force_authenticate(equipe["gestor"])
    politicas = api.get("/api/v1/sla/politicas/")
    assert politicas.status_code == 200
    media = next(p for p in politicas.data["results"] if p["prioridade"] == "MEDIA")
    url = f"/api/v1/sla/politicas/{media['id']}/"
    assert api.patch(url, {"minutos_resolucao": 999}, format="json").status_code == 200
    assert api.patch(url, {"minutos_resolucao": 0}, format="json").status_code == 400
    assert api.patch(url, {"prioridade": "ALTA"}, format="json").status_code == 400
    assert api.delete(url).status_code == 405
    novo = abrir()
    model = apps.get_model("chamados", "Chamado")
    assert model.objects.get(pk=antigo["id"]).sla_snapshot["MEDIA"] == 1440
    assert model.objects.get(pk=novo["id"]).sla_snapshot["MEDIA"] == 999


def test_indicadores_finais_e_cancelamento(api, equipe, abrir):
    chamado = abrir()
    dados = resolver(api, equipe, chamado)
    assert dados["sla"]["primeira_resposta"]["status"] == "CUMPRIDO"
    assert dados["sla"]["resolucao"]["status"] == "CUMPRIDO"
    cancelado = abrir()
    response = action(
        api,
        equipe,
        cancelado,
        "transicionar",
        {"status": "CANCELADO", "motivo": "Desisti"},
        papel="dono",
    )
    assert response.data["sla_status"] == "NAO_APLICAVEL"


def test_filtro_sla_respeita_visibilidade(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        meu = abrir()
        abrir(ator=equipe["outro"])
    with freeze_time(inicio + timedelta(minutes=121)):
        api.force_authenticate(equipe["dono"])
        response = api.get("/api/v1/chamados/?sla_status=VENCIDO")
        assert response.status_code == 200
        assert [x["id"] for x in response.data["results"]] == [meu["id"]]
        assert api.get("/api/v1/chamados/?sla_status=NO_PRAZO").data["count"] == 0


def test_filtros_sla_coincidem_com_indicador_pausado_e_final(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
        action(api, equipe, chamado, "assumir")
    with freeze_time(inicio + timedelta(hours=1)):
        action(
            api,
            equipe,
            chamado,
            "transicionar",
            {"status": "AGUARDANDO_SOLICITANTE", "motivo": "Pergunta"},
        )
    with freeze_time(inicio + timedelta(days=2)):
        dados = detalhe(api, equipe, chamado)
        assert dados["sla_status"] == "NO_PRAZO"
        assert api.get("/api/v1/chamados/?sla_status=NO_PRAZO").data["count"] == 1
        assert api.get("/api/v1/chamados/?sla_status=VENCIDO").data["count"] == 0
        action(api, equipe, chamado, "comentarios", {"texto": "Resposta"}, papel="dono")
        action(api, equipe, chamado, "transicionar", {"status": "RESOLVIDO", "motivo": "Feito"})
        api.force_authenticate(equipe["gestor"])
        assert api.get("/api/v1/chamados/?sla_status=CUMPRIDO").data["count"] == 1


def test_reabertura_nao_apaga_resultado_primeira_resposta(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir()
        action(api, equipe, chamado, "assumir")
    with freeze_time(inicio + timedelta(hours=3)):
        response = action(
            api, equipe, chamado, "transicionar", {"status": "RESOLVIDO", "motivo": "Feito"}
        )
        assert response.data["sla"]["primeira_resposta"]["status"] == "VIOLADO"
        response = action(api, equipe, chamado, "reabrir", {"motivo": "Falha"}, papel="dono")
        assert response.data["sla"]["primeira_resposta"]["status"] == "VIOLADO"
        assert response.data["sla"]["resolucao"]["status"] == "NO_PRAZO"


def test_prioridade_sem_motivo_e_chamado_resolvido(api, equipe, abrir):
    chamado = abrir()
    action(api, equipe, chamado, "assumir")
    assert action(api, equipe, chamado, "prioridade", {"prioridade": "ALTA"}).status_code == 400
    action(api, equipe, chamado, "transicionar", {"status": "RESOLVIDO", "motivo": "Feito"})
    assert (
        action(
            api,
            equipe,
            chamado,
            "prioridade",
            {"prioridade": "ALTA", "motivo": "Revisão"},
            papel="gestor",
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "segundos,estado",
    [(0, "NO_PRAZO"), (47, "NO_PRAZO"), (48, "EM_RISCO"), (60, "EM_RISCO"), (61, "VENCIDO")],
)
def test_filtro_resolucao_no_limite_e_primeira_resposta_concluida(
    api, equipe, abrir, segundos, estado
):
    apps.get_model("sla", "PoliticaSLA").objects.filter(prioridade="CRITICA").update(
        minutos_resolucao=1
    )
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
        action(api, equipe, chamado, "assumir")
        action(api, equipe, chamado, "comentarios", {"texto": "Iniciando atendimento"})
    with freeze_time(inicio + timedelta(seconds=segundos)):
        dados = detalhe(api, equipe, chamado)
        assert dados["sla_status"] == estado
        assert api.get(f"/api/v1/chamados/?sla_status={estado}").data["count"] == 1


def test_migracao_preserva_resultados_dos_chamados_existentes(api, equipe, abrir):
    from importlib import import_module
    from types import SimpleNamespace

    from django.db import connection

    inicio = timezone.now()
    with freeze_time(inicio):
        respondido = abrir()
        resolver(api, equipe, respondido)
        cancelado = abrir()
        action(
            api,
            equipe,
            cancelado,
            "transicionar",
            {"status": "CANCELADO", "motivo": "Desisti"},
            papel="dono",
        )
        sem_resposta = abrir()
        resolver(api, equipe, sem_resposta)
        aberto = abrir()
        atrasado = abrir(impacto="ALTO", urgencia="ALTA")
        action(api, equipe, atrasado, "assumir")
    with freeze_time(inicio + timedelta(hours=5)):
        action(
            api,
            equipe,
            atrasado,
            "transicionar",
            {"status": "RESOLVIDO", "motivo": "Solução tardia"},
        )
    model = apps.get_model("chamados", "Chamado")
    model.objects.update(primeira_resposta_resultado="", primeira_resposta_finalizada_em=None)
    model.objects.filter(pk=sem_resposta["id"]).update(primeira_resposta_em=None)
    apps.get_model("sla", "CicloResolucao").objects.update(violado_em=None)
    modulo = import_module("apps.sla.migrations.0004_resultados_existentes")
    modulo.preencher_resultados(apps, SimpleNamespace(connection=connection))
    assert model.objects.get(pk=respondido["id"]).primeira_resposta_resultado == "CUMPRIDO"
    assert model.objects.get(pk=cancelado["id"]).primeira_resposta_resultado == "NAO_APLICAVEL"
    assert model.objects.get(pk=sem_resposta["id"]).primeira_resposta_resultado == "VIOLADO"
    assert model.objects.get(pk=aberto["id"]).primeira_resposta_resultado == ""
    assert model.objects.get(pk=atrasado["id"]).ciclos.get().violado_em is not None


def test_resolucao_atrasada_registra_violacao_sem_job(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
        action(api, equipe, chamado, "assumir")
    with freeze_time(inicio + timedelta(hours=5)):
        action(
            api, equipe, chamado, "transicionar", {"status": "RESOLVIDO", "motivo": "Finalizado"}
        )
    ciclo = apps.get_model("sla", "CicloResolucao").objects.get(chamado_id=chamado["id"])
    assert ciclo.resultado == "VIOLADO"
    assert ciclo.violado_em == inicio + timedelta(hours=5)


def test_repetir_prioridade_nao_cria_evento(api, equipe, abrir):
    chamado = abrir()
    action(api, equipe, chamado, "assumir")
    assert (
        action(
            api, equipe, chamado, "prioridade", {"prioridade": "MEDIA", "motivo": "Sem mudança"}
        ).status_code
        == 409
    )
    obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
    assert not obj.eventos.filter(tipo="PRIORIDADE_ALTERADA").exists()
