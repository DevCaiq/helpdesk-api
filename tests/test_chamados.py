from datetime import timedelta

import pytest
from django.apps import apps
from django.core.management import call_command
from django.utils import timezone
from freezegun import freeze_time

from tests.helpers import action, resolver

pytestmark = pytest.mark.django_db
BASE = "/api/v1/chamados/"


def test_abertura_e_prazos(api, equipe, abrir):
    now = timezone.now()
    with freeze_time(now):
        chamado = abrir(impacto="ALTO", urgencia="ALTA")
    assert chamado["status"] == "ABERTO" and chamado["nivel_atual"] == "N1"
    assert chamado["responsavel"] is None and chamado["prioridade"] == "CRITICA"
    model = apps.get_model("chamados", "Chamado")
    obj = model.objects.get(pk=chamado["id"])
    assert obj.prazo_primeira_resposta == now + timedelta(hours=2)
    ciclo = obj.ciclos.get()
    assert ciclo.prazo == now + timedelta(hours=4)
    assert len(obj.sla_snapshot) == 4
    assert obj.historico.get().status_novo == "ABERTO"


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("prioridade", "CRITICA"),
        ("status", "FECHADO"),
        ("nivel_atual", "N2"),
        ("responsavel", 1),
        ("solicitante", 1),
        ("sla_snapshot", {}),
    ],
)
def test_abertura_rejeita_campos_controlados(api, equipe, categoria, campo, valor):
    api.force_authenticate(equipe["dono"])
    response = api.post(
        BASE,
        {
            "titulo": "Teste",
            "descricao": "Texto",
            "categoria": categoria,
            "impacto": "BAIXO",
            "urgencia": "BAIXA",
            campo: valor,
        },
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "papel,status", [("dono", 200), ("outro", 404), ("n1", 200), ("n2", 404), ("gestor", 200)]
)
def test_visibilidade_detalhe_lista_historico_comentarios(api, equipe, abrir, papel, status):
    chamado = abrir()
    api.force_authenticate(equipe[papel])
    for sufixo in ["", "historico/", "comentarios/"]:
        assert api.get(BASE + f"{chamado['id']}/" + sufixo).status_code == status
    response = api.get(BASE)
    assert response.status_code == 200
    assert response.data["count"] == (1 if status == 200 else 0)


def test_analista_ve_chamado_proprio_fora_da_fila(api, equipe, abrir):
    chamado = abrir(ator=equipe["n2"])
    api.force_authenticate(equipe["n2"])
    assert api.get(BASE + f"{chamado['id']}/").status_code == 200


def test_assumir_muda_status_sem_primeira_resposta(api, equipe, abrir):
    chamado = abrir()
    response = action(api, equipe, chamado, "assumir")
    assert response.status_code == 200
    assert response.data["status"] == "EM_ATENDIMENTO"
    assert response.data["responsavel"] == equipe["n1"].pk
    assert response.data["primeira_resposta_em"] is None
    assert action(api, equipe, chamado, "assumir", papel="n1b").status_code == 409


def test_somente_responsavel_conduz(api, equipe, abrir):
    chamado = abrir()
    action(api, equipe, chamado, "assumir")
    assert (
        action(
            api,
            equipe,
            chamado,
            "transicionar",
            {"status": "RESOLVIDO", "motivo": "Feito"},
            papel="n1b",
        ).status_code
        == 403
    )
    assert (
        action(
            api, equipe, chamado, "comentarios", {"texto": "Interferência"}, papel="n1b"
        ).status_code
        == 403
    )


def test_notas_internas_nao_vazam(api, equipe, abrir):
    chamado = abrir()
    action(api, equipe, chamado, "assumir")
    assert (
        action(
            api, equipe, chamado, "comentarios", {"texto": "SEGREDO_INTERNO", "interno": True}
        ).status_code
        == 201
    )
    api.force_authenticate(equipe["dono"])
    response = api.get(BASE + f"{chamado['id']}/comentarios/")
    assert response.data["count"] == 0
    for sufixo in ["", "historico/"]:
        assert "SEGREDO_INTERNO" not in str(api.get(BASE + f"{chamado['id']}/" + sufixo).data)
    assert (
        action(
            api,
            equipe,
            chamado,
            "comentarios",
            {"texto": "Tentativa", "interno": True},
            papel="dono",
        ).status_code
        == 403
    )


def test_gestor_solicitante_nao_ve_nota_interna(api, equipe, abrir):
    chamado = abrir(ator=equipe["gestor"])
    action(api, equipe, chamado, "assumir")
    action(api, equipe, chamado, "comentarios", {"texto": "Interno", "interno": True})
    api.force_authenticate(equipe["gestor"])
    assert api.get(BASE + f"{chamado['id']}/comentarios/").data["count"] == 0


def test_pausa_resposta_e_resolucao(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir()
        action(api, equipe, chamado, "assumir")
    with freeze_time(inicio + timedelta(hours=1)):
        response = action(
            api,
            equipe,
            chamado,
            "transicionar",
            {"status": "AGUARDANDO_SOLICITANTE", "motivo": "Informe o erro"},
        )
        assert response.status_code == 200
    with freeze_time(inicio + timedelta(hours=3)):
        response = action(
            api, equipe, chamado, "comentarios", {"texto": "Erro de acesso"}, papel="dono"
        )
        assert response.status_code == 201
    obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
    assert obj.status == "EM_ATENDIMENTO"
    assert obj.primeira_resposta_em == inicio + timedelta(hours=1)
    assert obj.prazo_primeira_resposta == inicio + timedelta(hours=2)
    ciclo = obj.ciclos.get()
    assert ciclo.prazo == inicio + timedelta(hours=26)
    assert ciclo.pausas.get().fim == inicio + timedelta(hours=3)


def test_reabertura_preserva_ciclo_e_primeira_resposta(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir()
        resolver(api, equipe, chamado)
    with freeze_time(inicio + timedelta(hours=47)):
        response = action(
            api, equipe, chamado, "reabrir", {"motivo": "Falha retornou"}, papel="dono"
        )
        assert response.status_code == 200
    obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
    assert obj.status == "REABERTO" and obj.responsavel is None
    assert obj.ciclos.count() == 2 and obj.ciclos.filter(resolvido_em__isnull=False).count() == 1
    assert obj.primeira_resposta_em == inicio


@pytest.mark.parametrize(
    "acao,dados",
    [
        ("reabrir", {"motivo": "Tarde"}),
        ("comentarios", {"texto": "Tarde"}),
        ("assumir", {}),
        ("reatribuir", {"responsavel": 1}),
    ],
)
def test_prazo_encerrado_bloqueia_mutacoes_inclusive_gestor(api, equipe, abrir, acao, dados):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir()
        resolver(api, equipe, chamado)
    with freeze_time(inicio + timedelta(hours=48)):
        assert action(api, equipe, chamado, acao, dados, papel="gestor").status_code == 409
        api.force_authenticate(equipe["gestor"])
        assert (
            api.patch(BASE + f"{chamado['id']}/", {"titulo": "Alterado"}, format="json").status_code
            == 409
        )


def test_interacao_adia_fechamento_sem_ampliar_reabertura(api, equipe, abrir):
    inicio = timezone.now()
    with freeze_time(inicio):
        chamado = abrir()
        resolver(api, equipe, chamado)
    with freeze_time(inicio + timedelta(hours=40)):
        assert (
            action(
                api, equipe, chamado, "comentarios", {"texto": "Obrigado"}, papel="dono"
            ).status_code
            == 201
        )
    with freeze_time(inicio + timedelta(hours=49)):
        assert (
            action(api, equipe, chamado, "reabrir", {"motivo": "Tarde"}, papel="dono").status_code
            == 409
        )
        call_command("fechar_resolvidos")
        obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
        assert obj.status == "RESOLVIDO"
    with freeze_time(inicio + timedelta(hours=88)):
        call_command("fechar_resolvidos")
        call_command("fechar_resolvidos")
    obj.refresh_from_db()
    assert obj.status == "FECHADO"
    assert obj.historico.filter(status_novo="FECHADO").count() == 1


def test_edicao_dono_apenas_aberto(api, equipe, abrir):
    chamado = abrir()
    api.force_authenticate(equipe["dono"])
    assert (
        api.patch(BASE + f"{chamado['id']}/", {"titulo": "Mais claro"}, format="json").status_code
        == 200
    )
    action(api, equipe, chamado, "assumir")
    api.force_authenticate(equipe["dono"])
    assert (
        api.patch(BASE + f"{chamado['id']}/", {"titulo": "Outra edição"}, format="json").status_code
        == 403
    )


def test_reatribuicao_exige_analista_ativo_nivel_compativel(api, equipe, abrir):
    chamado = abrir()
    assert (
        action(
            api, equipe, chamado, "reatribuir", {"responsavel": equipe["n2"].pk}, papel="gestor"
        ).status_code
        == 400
    )
    assert (
        action(
            api, equipe, chamado, "reatribuir", {"responsavel": equipe["n1"].pk}, papel="dono"
        ).status_code
        == 403
    )
    assert (
        action(
            api, equipe, chamado, "reatribuir", {"responsavel": equipe["n1"].pk}, papel="gestor"
        ).status_code
        == 200
    )


def test_transicoes_invalidas_e_cancelamento(api, equipe, abrir):
    chamado = abrir()
    assert (
        action(
            api,
            equipe,
            chamado,
            "transicionar",
            {"status": "RESOLVIDO", "motivo": "Pular"},
            papel="gestor",
        ).status_code
        == 409
    )
    assert (
        action(
            api,
            equipe,
            chamado,
            "transicionar",
            {"status": "CANCELADO", "motivo": "Desisti"},
            papel="dono",
        ).status_code
        == 200
    )
    assert (
        action(api, equipe, chamado, "comentarios", {"texto": "Tarde"}, papel="gestor").status_code
        == 409
    )


def test_categoria_inativa_e_escrita_restrita(api, equipe, categoria):
    api.force_authenticate(equipe["dono"])
    assert api.post("/api/v1/categorias/", {"nome": "Nova"}, format="json").status_code == 403
    api.force_authenticate(equipe["gestor"])
    assert (
        api.patch(f"/api/v1/categorias/{categoria}/", {"ativa": False}, format="json").status_code
        == 200
    )
    api.force_authenticate(equipe["dono"])
    assert (
        api.post(
            BASE,
            {
                "titulo": "Teste",
                "descricao": "Texto",
                "categoria": categoria,
                "impacto": "ALTO",
                "urgencia": "ALTA",
            },
            format="json",
        ).status_code
        == 400
    )


@pytest.mark.parametrize(
    "impacto,urgencia,prioridade",
    [
        ("ALTO", "ALTA", "CRITICA"),
        ("ALTO", "MEDIA", "ALTA"),
        ("ALTO", "BAIXA", "MEDIA"),
        ("MEDIO", "ALTA", "ALTA"),
        ("MEDIO", "MEDIA", "MEDIA"),
        ("MEDIO", "BAIXA", "BAIXA"),
        ("BAIXO", "ALTA", "MEDIA"),
        ("BAIXO", "MEDIA", "BAIXA"),
        ("BAIXO", "BAIXA", "BAIXA"),
    ],
)
def test_matriz_prioridade(abrir, impacto, urgencia, prioridade):
    assert abrir(impacto=impacto, urgencia=urgencia)["prioridade"] == prioridade


@pytest.mark.parametrize(
    "acao,dados",
    [
        ("assumir", {}),
        ("reabrir", {"motivo": "Teste"}),
        ("transicionar", {"status": "CANCELADO", "motivo": "Teste"}),
        ("reatribuir", {"responsavel": 1}),
        ("comentarios", {"texto": "Teste"}),
    ],
)
def test_acoes_ocultas_retornam_404(api, equipe, abrir, acao, dados):
    chamado = abrir()
    assert action(api, equipe, chamado, acao, dados, papel="outro").status_code == 404


def test_assuncao_sem_perfil_nivel_corretos(api, equipe, abrir):
    chamado = abrir(ator=equipe["n2"])
    assert action(api, equipe, chamado, "assumir", papel="n2").status_code == 403
    assert action(api, equipe, chamado, "assumir", papel="gestor").status_code == 403
    assert action(api, equipe, chamado, "assumir", papel="outro").status_code == 404


def test_confirmar_fechamento_terminal(api, equipe, abrir):
    chamado = abrir()
    resolver(api, equipe, chamado)
    response = action(
        api,
        equipe,
        chamado,
        "transicionar",
        {"status": "FECHADO", "motivo": "Confirmado"},
        papel="dono",
    )
    assert response.status_code == 200 and response.data["fechado_em"] is not None
    assert (
        action(
            api, equipe, chamado, "reabrir", {"motivo": "Não permitido"}, papel="gestor"
        ).status_code
        == 409
    )


def test_historico_nao_permite_alteracao_exclusao_ou_upsert(abrir):
    from django.core.exceptions import ValidationError

    chamado = abrir()
    model = apps.get_model("chamados", "HistoricoStatus")
    event = model.objects.get(chamado_id=chamado["id"])
    with pytest.raises(ValidationError):
        event.save()
    with pytest.raises(ValidationError):
        event.delete()
    with pytest.raises(ValidationError):
        model.objects.filter(pk=event.pk).update(motivo="Alterado")
    with pytest.raises(ValidationError):
        model.objects.filter(pk=event.pk).delete()
    with pytest.raises(ValidationError):
        model.objects.bulk_create(
            [model(pk=event.pk, chamado_id=chamado["id"], status_novo="FECHADO")],
            update_conflicts=True,
            update_fields=["status_novo"],
            unique_fields=["id"],
        )


def test_falha_auditoria_reverte_resolucao_comentario_e_ciclo(api, equipe, abrir, monkeypatch):
    from apps.chamados import services

    chamado = abrir()
    action(api, equipe, chamado, "assumir")

    def falha(*args, **kwargs):
        raise RuntimeError("Auditoria indisponível")

    monkeypatch.setattr(services, "auditar", falha)
    with pytest.raises(RuntimeError):
        action(api, equipe, chamado, "transicionar", {"status": "RESOLVIDO", "motivo": "Feito"})
    obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
    assert obj.status == "EM_ATENDIMENTO" and obj.primeira_resposta_em is None
    assert obj.comentarios.count() == 0 and obj.historico.count() == 2
    assert obj.ciclos.get().encerrado_em is None


def test_edicao_politica_nao_muda_snapshot_na_reabertura(api, equipe, abrir):
    chamado = abrir()
    apps.get_model("sla", "PoliticaSLA").objects.filter(prioridade="MEDIA").update(
        minutos_resolucao=999
    )
    resolver(api, equipe, chamado)
    assert (
        action(api, equipe, chamado, "reabrir", {"motivo": "Retornou"}, papel="dono").status_code
        == 200
    )
    obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
    assert obj.ciclos.last().minutos_aplicados == 1440
    novo = abrir()
    assert (
        apps.get_model("chamados", "Chamado")
        .objects.get(pk=novo["id"])
        .ciclos.get()
        .minutos_aplicados
        == 999
    )


def test_reatribuicao_rejeita_inativo(api, equipe, abrir):
    chamado = abrir()
    equipe["n1"].is_active = False
    equipe["n1"].save()
    assert (
        action(
            api, equipe, chamado, "reatribuir", {"responsavel": equipe["n1"].pk}, papel="gestor"
        ).status_code
        == 400
    )


def test_categoria_utilizada_nao_pode_ser_excluida(api, equipe, abrir, categoria):
    abrir()
    api.force_authenticate(equipe["gestor"])
    assert api.delete(f"/api/v1/categorias/{categoria}/").status_code == 409
    response = api.post("/api/v1/categorias/", {"nome": "Livre"}, format="json")
    assert response.status_code == 201
    assert api.delete(f"/api/v1/categorias/{response.data['id']}/").status_code == 204


def test_busca_filtro_e_ordenacao_respeitam_visibilidade(api, equipe, abrir):
    um = abrir(titulo="VPN", impacto="ALTO", urgencia="ALTA")
    abrir(ator=equipe["outro"], titulo="VPN de outro")
    api.force_authenticate(equipe["dono"])
    response = api.get(BASE + "?search=VPN&prioridade=CRITICA&ordering=id")
    assert response.status_code == 200
    assert [obj["id"] for obj in response.data["results"]] == [um["id"]]


def test_nota_interna_nao_marca_primeira_resposta(api, equipe, abrir):
    chamado = abrir()
    action(api, equipe, chamado, "assumir")
    assert (
        action(
            api, equipe, chamado, "comentarios", {"texto": "Análise interna", "interno": True}
        ).status_code
        == 201
    )
    obj = apps.get_model("chamados", "Chamado").objects.get(pk=chamado["id"])
    assert obj.primeira_resposta_em is None


def test_motivo_publico_obrigatorio_para_espera_e_resolucao(api, equipe, abrir):
    chamado = abrir()
    action(api, equipe, chamado, "assumir")
    for destino in ("AGUARDANDO_SOLICITANTE", "RESOLVIDO"):
        assert action(api, equipe, chamado, "transicionar", {"status": destino}).status_code == 400


def test_analista_que_nao_e_dono_nao_reabre_ou_cancela(api, equipe, abrir):
    chamado = abrir()
    assert (
        action(
            api, equipe, chamado, "transicionar", {"status": "CANCELADO", "motivo": "Indevido"}
        ).status_code
        == 403
    )
    resolver(api, equipe, chamado)
    assert action(api, equipe, chamado, "reabrir", {"motivo": "Indevido"}).status_code == 403


def test_transicionar_reabertura_usa_mesmas_regras(api, equipe, abrir):
    chamado = abrir()
    resolver(api, equipe, chamado)
    assert (
        action(
            api,
            equipe,
            chamado,
            "transicionar",
            {"status": "REABERTO", "motivo": "Falha"},
            papel="dono",
        ).status_code
        == 200
    )


def test_respostas_retornam_ciclos_atualizados(api, equipe, abrir):
    chamado = abrir()
    resolvido = resolver(api, equipe, chamado)
    assert resolvido["ciclos"][0]["resolvido_em"] is not None
    response = action(api, equipe, chamado, "reabrir", {"motivo": "Falha retornou"}, papel="dono")
    assert len(response.data["ciclos"]) == 2
    assert response.data["ciclos"][-1]["resolvido_em"] is None


def test_assuncao_audita_responsavel_anterior_e_novo(api, equipe, abrir):
    chamado = abrir()
    action(api, equipe, chamado, "assumir")
    evento = (
        apps.get_model("auditoria", "LogAuditoria")
        .objects.filter(acao="CHAMADO_ASSUMIDO", entidade="chamado", entidade_id=str(chamado["id"]))
        .first()
    )
    assert evento is not None
    assert evento.antes["responsavel_id"] is None
    assert evento.depois["responsavel_id"] == equipe["n1"].pk


def test_listagem_nao_faz_query_por_ciclo(api, equipe, abrir, django_assert_num_queries):
    for _ in range(4):
        abrir()
    api.force_authenticate(equipe["dono"])
    with django_assert_num_queries(3):
        response = api.get(BASE)
    assert response.status_code == 200 and response.data["count"] == 4


def test_admin_oculta_nota_interna_do_proprio_solicitante(api, equipe, abrir, client):
    gestor = equipe["gestor"]
    gestor.is_staff = True
    gestor.is_superuser = True
    gestor.save()
    chamado = abrir(ator=gestor)
    action(api, equipe, chamado, "assumir")
    response = action(
        api,
        equipe,
        chamado,
        "comentarios",
        {"texto": "CONTEUDO_PRIVADO_NUNCA_EXIBIR", "interno": True},
    )
    client.force_login(gestor)
    resposta_admin = client.get(
        f"/admin/chamados/comentario/{response.data['id']}/change/", follow=True
    )
    assert b"CONTEUDO_PRIVADO_NUNCA_EXIBIR" not in resposta_admin.content


def test_auditoria_reabertura_preserva_responsavel_anterior(api, equipe, abrir):
    chamado = abrir()
    resolver(api, equipe, chamado)
    action(api, equipe, chamado, "reabrir", {"motivo": "Falha retornou"}, papel="dono")
    model = apps.get_model("auditoria", "LogAuditoria")
    event = model.objects.filter(
        acao="STATUS_ALTERADO", entidade="chamado", entidade_id=str(chamado["id"])
    ).first()
    assert event.antes["responsavel_id"] == equipe["n1"].pk
    assert event.depois["responsavel_id"] is None
