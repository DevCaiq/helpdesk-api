from datetime import timedelta

import pytest
from django.apps import apps
from django.core.management import call_command
from django.utils import timezone
from freezegun import freeze_time

from tests.helpers import action

pytestmark = pytest.mark.django_db


def triar(api, equipe, chamado, papel="n1"):
    return action(api, equipe, chamado, "triar", {"motivo": "Triagem concluída"}, papel=papel)


@pytest.mark.parametrize("papel,status", [("dono", 403), ("gestor", 403), ("n1", 200), ("n2", 404)])
def test_triagem_exige_n1_nao_solicitante(api, equipe, abrir, papel, status):
    chamado = abrir()
    assert triar(api, equipe, chamado, papel).status_code == status


def test_n1_nao_tria_proprio_chamado(api, equipe, abrir):
    chamado = abrir(ator=equipe["n1"])
    assert triar(api, equipe, chamado).status_code == 403


def test_triagem_de_atribuido_exige_responsavel(api, equipe, abrir):
    chamado = abrir()
    action(api, equipe, chamado, "assumir")
    assert triar(api, equipe, chamado, "n1b").status_code == 403
    assert triar(api, equipe, chamado).status_code == 200
    assert triar(api, equipe, chamado).status_code == 409


def test_escalada_manual_exige_triagem_preserva_status_prazos(api, equipe, abrir):
    chamado = abrir()
    action(api, equipe, chamado, "assumir")
    assert action(api, equipe, chamado, "escalar", {"motivo": "Precisa N2"}).status_code == 409
    assert triar(api, equipe, chamado).status_code == 200
    response = action(api, equipe, chamado, "escalar", {"motivo": "Precisa N2"})
    assert response.status_code == 200
    assert response.data["nivel_atual"] == "N2" and response.data["responsavel"] is None
    assert response.data["status"] == "EM_ATENDIMENTO"
    assert response.data["ciclos"][0]["prazo"] == chamado["ciclos"][0]["prazo"]
    assert (
        action(api, equipe, chamado, "escalar", {"motivo": "Repetir"}, papel="gestor").status_code
        == 409
    )
    assert action(api, equipe, chamado, "assumir", papel="n2").status_code == 200


def test_critico_sem_triagem_apenas_alerta_e_job_idempotente(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
    with freeze_time(inicio + timedelta(minutes=10)):
        call_command("verificar_sla")
        call_command("verificar_sla")
    obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
    assert obj.nivel_atual == "N1"
    alerta = apps.get_model("sla", "AlertaSLA")
    assert alerta.objects.filter(chamado=obj, tipo="CRITICO_SEM_RESPONSAVEL").count() == 1


def test_critico_triado_escala_aos_dez_minutos(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
        assert triar(api, equipe, chamado).status_code == 200
    with freeze_time(inicio + timedelta(minutes=9)):
        call_command("verificar_sla")
        obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
        assert obj.nivel_atual == "N1"
    with freeze_time(inicio + timedelta(minutes=10)):
        call_command("verificar_sla")
        call_command("verificar_sla")
    obj.refresh_from_db()
    assert obj.nivel_atual == "N2"
    assert obj.eventos.filter(tipo="ESCALADO").count() == 1


def test_resolucao_em_risco_escala_somente_apos_triagem(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
        action(api, equipe, chamado, "assumir")
    with freeze_time(inicio + timedelta(minutes=192)):
        call_command("verificar_sla")
        obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
        assert obj.nivel_atual == "N1"
        assert triar(api, equipe, chamado).status_code == 200
        call_command("verificar_sla")
    obj.refresh_from_db()
    assert obj.nivel_atual == "N2" and obj.responsavel is None


@pytest.mark.parametrize("estado", ["AGUARDANDO_SOLICITANTE", "RESOLVIDO", "CANCELADO"])
def test_job_nao_escala_espera_ou_terminais(api, equipe, abrir, estado):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
        triar(api, equipe, chamado)
        if estado != "CANCELADO":
            action(api, equipe, chamado, "assumir")
        action(
            api,
            equipe,
            chamado,
            "transicionar",
            {"status": estado, "motivo": "Motivo"},
            papel="dono" if estado == "CANCELADO" else "n1",
        )
    with freeze_time(inicio + timedelta(days=3)):
        call_command("verificar_sla")
    obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
    assert obj.nivel_atual == "N1"
    if estado == "RESOLVIDO":
        assert obj.status == "FECHADO"


@pytest.mark.parametrize("papel,status", [("dono", 403), ("n1", 200), ("n2", 403), ("gestor", 200)])
def test_alertas_acesso_restrito(api, equipe, abrir, papel, status):
    inicio = timezone.now()
    with freeze_time(inicio):
        abrir(impacto="ALTO", urgencia="ALTA")
    with freeze_time(inicio + timedelta(minutes=10)):
        call_command("verificar_sla")
    api.force_authenticate(equipe[papel])
    response = api.get("/api/v1/alertas/")
    assert response.status_code == status
    if status == 200:
        assert response.data["count"] == 1


def test_motivo_interno_evento_oculto_ao_dono(api, equipe, abrir):
    chamado = abrir()
    assert action(api, equipe, chamado, "triar", {"motivo": "DETALHE_INTERNO"}).status_code == 200
    api.force_authenticate(equipe["dono"])
    response = api.get(f"/api/v1/chamados/{chamado['id']}/eventos/")
    assert response.status_code == 403
    assert "DETALHE_INTERNO" not in str(api.get(f"/api/v1/chamados/{chamado['id']}/").data)
    api.force_authenticate(equipe["n1"])
    assert (
        api.get(f"/api/v1/chamados/{chamado['id']}/eventos/").data["results"][0]["motivo"]
        == "DETALHE_INTERNO"
    )


def test_job_rollback_escalada_e_alertas_se_auditoria_falha(api, equipe, abrir, monkeypatch):
    from apps.chamados import services_escalonamento

    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
        triar(api, equipe, chamado)

    def falha(*args, **kwargs):
        raise RuntimeError("Auditoria indisponível")

    monkeypatch.setattr(services_escalonamento, "auditar", falha)
    with freeze_time(inicio + timedelta(minutes=10)), pytest.raises(RuntimeError):
        call_command("verificar_sla")
    obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
    assert obj.nivel_atual == "N1"
    assert not obj.alertas.exists() and not obj.eventos.filter(tipo="ESCALADO").exists()


def test_eventos_e_alertas_imutaveis(api, equipe, abrir):
    from django.core.exceptions import ValidationError

    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
        triar(api, equipe, chamado)
    with freeze_time(inicio + timedelta(minutes=10)):
        call_command("verificar_sla")
    obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
    for evento in [obj.eventos.first(), obj.alertas.first()]:
        with pytest.raises(ValidationError):
            evento.save()
        with pytest.raises(ValidationError):
            type(evento).objects.filter(pk=evento.pk).delete()


def test_loop_local_e_intervalo_invalido(monkeypatch):
    from django.core.management.base import CommandError

    from apps.sla.management.commands import verificar_sla

    with pytest.raises(CommandError):
        call_command("verificar_sla", continuo=True, intervalo=0)

    def parar(segundos):
        assert segundos == 1
        raise KeyboardInterrupt

    monkeypatch.setattr(verificar_sla.time, "sleep", parar)
    call_command("verificar_sla", continuo=True, intervalo=1)


def test_gestor_solicitante_nao_escala_proprio_chamado(api, equipe, abrir):
    chamado = abrir(ator=equipe["gestor"])
    triar(api, equipe, chamado)
    assert (
        action(
            api, equipe, chamado, "escalar", {"motivo": "Não permitido"}, papel="gestor"
        ).status_code
        == 403
    )


def test_n1_nao_responsavel_nao_escala_atribuido(api, equipe, abrir):
    chamado = abrir()
    action(api, equipe, chamado, "assumir")
    triar(api, equipe, chamado)
    assert (
        action(
            api, equipe, chamado, "escalar", {"motivo": "Não permitido"}, papel="n1b"
        ).status_code
        == 403
    )


def test_mudanca_de_nivel_impede_escalada_por_antigo_n1(api, equipe, abrir):
    chamado = abrir()
    action(api, equipe, chamado, "assumir")
    triar(api, equipe, chamado)
    api.force_authenticate(equipe["gestor"])
    assert (
        api.patch(
            f"/api/v1/usuarios/{equipe['n1'].pk}/", {"nivel": "N2"}, format="json"
        ).status_code
        == 200
    )
    equipe["n1"].refresh_from_db()
    assert action(api, equipe, chamado, "escalar", {"motivo": "Não permitido"}).status_code == 403
