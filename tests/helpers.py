BASE = "/api/v1/chamados/"


def action(api, equipe, chamado, acao, dados=None, papel="n1"):
    api.force_authenticate(equipe[papel])
    return api.post(BASE + f"{chamado['id']}/{acao}/", dados or {}, format="json")


def resolver(api, equipe, chamado):
    assert action(api, equipe, chamado, "assumir").status_code == 200
    response = action(
        api, equipe, chamado, "transicionar", {"status": "RESOLVIDO", "motivo": "Acesso restaurado"}
    )
    assert response.status_code == 200, response.data
    return response.data
