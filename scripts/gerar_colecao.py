"""Gera coleção Postman pública sem credenciais ou dependências de Django."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / "collections" / "postman"


def requisicao(
    nome,
    metodo,
    caminho,
    status=200,
    papel=None,
    corpo=None,
    capturar=None,
    testes=(),
    formulario=False,
):
    request = {"method": metodo, "url": "{{base_url}}" + caminho, "header": []}
    if papel:
        request["auth"] = {
            "type": "bearer",
            "bearer": [{"key": "token", "value": "{{access_" + papel + "}}", "type": "string"}],
        }
    else:
        request["auth"] = {"type": "noauth"}
    if corpo is not None:
        if formulario:
            request["body"] = {
                "mode": "urlencoded",
                "urlencoded": [{"key": k, "value": v, "type": "text"} for k, v in corpo.items()],
            }
            request["header"].append(
                {"key": "Content-Type", "value": "application/x-www-form-urlencoded"}
            )
        else:
            raw = json.dumps(corpo, ensure_ascii=False, indent=2)
            raw = raw.replace('"{{categoria_id}}"', "{{categoria_id}}")
            request["body"] = {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}
            request["header"].append({"key": "Content-Type", "value": "application/json"})
    linhas = [f'pm.test("HTTP {status}", function () {{ pm.response.to.have.status({status}); }});']
    if capturar or testes:
        linhas.append("const body = pm.response.json();")
    for variavel, campo in (capturar or {}).items():
        linhas.append(f'pm.environment.set("{variavel}", body.{campo});')
    linhas.extend(testes)
    return {
        "name": nome,
        "request": request,
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": linhas}}],
    }


def login(papel):
    return requisicao(
        f"Login {papel}",
        "POST",
        "/api/v1/auth/login/",
        corpo={"email": "{{" + papel + "_email}}", "password": "{{" + papel + "_password}}"},
        formulario=True,
        capturar={f"access_{papel}": "access", f"refresh_{papel}": "refresh"},
        testes=[
            'pm.test("Tokens presentes", function () { '
            'pm.expect(body.access).to.be.a("string"); '
            'pm.expect(body.refresh).to.be.a("string"); });'
        ],
    )


def construir():
    url = "/api/v1/chamados/{{chamado_fluxo_id}}/"
    items = [
        requisicao("00 - Saúde", "GET", "/health/"),
        login("solicitante"),
        requisicao("02 - Meu perfil", "GET", "/api/v1/usuarios/me/", papel="solicitante"),
        requisicao(
            "03 - IDOR bloqueado",
            "GET",
            "/api/v1/chamados/{{demo_outro_id}}/",
            404,
            papel="solicitante",
        ),
        requisicao(
            "04 - Métricas negadas ao solicitante",
            "GET",
            "/api/v1/metricas/volume/",
            403,
            papel="solicitante",
        ),
        requisicao(
            "05 - Abrir novo fluxo",
            "POST",
            "/api/v1/chamados/",
            201,
            papel="solicitante",
            corpo={
                "titulo": "Fluxo da coleção Postman",
                "descricao": "Demonstração de ponta a ponta com dados fictícios.",
                "categoria": "{{categoria_id}}",
                "impacto": "MEDIO",
                "urgencia": "MEDIA",
            },
            capturar={"chamado_fluxo_id": "id"},
        ),
        login("n1"),
        requisicao(
            "07 - Triagem N1",
            "POST",
            url + "triar/",
            papel="n1",
            corpo={"motivo": "Triagem concluída pela coleção."},
        ),
        requisicao("08 - Assumir N1", "POST", url + "assumir/", papel="n1", corpo={}),
        requisicao(
            "09 - Nota interna",
            "POST",
            url + "comentarios/",
            201,
            papel="n1",
            corpo={"texto": "Nota interna da coleção, oculta do solicitante.", "interno": True},
        ),
        requisicao(
            "10 - Aguardar solicitante",
            "POST",
            url + "transicionar/",
            papel="n1",
            corpo={"status": "AGUARDANDO_SOLICITANTE", "motivo": "Informe o detalhe da falha."},
        ),
        requisicao(
            "11 - Notas internas ocultas",
            "GET",
            url + "comentarios/",
            papel="solicitante",
            testes=[
                'pm.test("Somente comentários públicos", function () { '
                "pm.expect(body.results.every(function (x) { "
                "return x.interno === false; })).to.eql(true); });"
            ],
        ),
        requisicao(
            "12 - Responder e retomar",
            "POST",
            url + "comentarios/",
            201,
            papel="solicitante",
            corpo={"texto": "Detalhe da falha informado."},
        ),
        requisicao(
            "13 - Escalar N2 após triagem",
            "POST",
            url + "escalar/",
            papel="n1",
            corpo={"motivo": "Análise fictícia exige especialista N2."},
        ),
        login("n2"),
        requisicao("15 - Assumir N2", "POST", url + "assumir/", papel="n2", corpo={}),
        requisicao(
            "16 - Resolver N2",
            "POST",
            url + "transicionar/",
            papel="n2",
            corpo={"status": "RESOLVIDO", "motivo": "Solução aplicada pelo N2."},
        ),
        requisicao(
            "17 - Reabrir no prazo",
            "POST",
            url + "reabrir/",
            papel="solicitante",
            corpo={"motivo": "Falha fictícia retornou."},
        ),
        requisicao("18 - Reassumir N2", "POST", url + "assumir/", papel="n2", corpo={}),
        requisicao(
            "19 - Resolver definitivamente",
            "POST",
            url + "transicionar/",
            papel="n2",
            corpo={"status": "RESOLVIDO", "motivo": "Solução final validada."},
        ),
        requisicao(
            "20 - Confirmar fechamento",
            "POST",
            url + "transicionar/",
            papel="solicitante",
            corpo={"status": "FECHADO", "motivo": "Confirmado pelo solicitante."},
        ),
        login("gestor"),
        requisicao("22 - Volume de chamados", "GET", "/api/v1/metricas/volume/", papel="gestor"),
        requisicao("23 - Indicadores de SLA", "GET", "/api/v1/metricas/sla/", papel="gestor"),
        requisicao(
            "24 - Auditoria do fluxo",
            "GET",
            "/api/v1/auditoria/?entidade=chamado&entidade_id={{chamado_fluxo_id}}",
            papel="gestor",
            testes=[
                'pm.test("Fluxo auditado", function () { pm.expect(body.count).to.be.above(0); });'
            ],
        ),
        requisicao(
            "25 - Fechado não aceita comentário",
            "POST",
            url + "comentarios/",
            409,
            papel="solicitante",
            corpo={"texto": "Tentativa bloqueada."},
        ),
        requisicao(
            "26 - Rotacionar refresh",
            "POST",
            "/api/v1/auth/refresh/",
            corpo={"refresh": "{{refresh_solicitante}}"},
            capturar={"access_solicitante": "access", "refresh_solicitante": "refresh"},
        ),
        requisicao(
            "27 - Logout",
            "POST",
            "/api/v1/auth/logout/",
            204,
            papel="solicitante",
            corpo={"refresh": "{{refresh_solicitante}}"},
        ),
        requisicao(
            "28 - Refresh revogado bloqueado",
            "POST",
            "/api/v1/auth/refresh/",
            401,
            corpo={"refresh": "{{refresh_solicitante}}"},
        ),
    ]
    return {
        "info": {
            "name": "Gestão de Chamados - Fluxo completo local",
            "description": (
                "Execute na ordem com o ambiente privado gerado por seed_demo. "
                "Cada rodada abre um novo chamado; sem senhas nesta coleção."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [{"key": "base_url", "value": "http://127.0.0.1:8000", "type": "string"}],
        "item": items,
    }


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    (DESTINO / "helpdesk.postman_collection.json").write_text(
        json.dumps(construir(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    valores = [
        {"key": "base_url", "value": "http://127.0.0.1:8000", "enabled": True, "type": "default"},
        {"key": "categoria_id", "value": "", "enabled": True, "type": "default"},
        {"key": "demo_outro_id", "value": "", "enabled": True, "type": "default"},
    ]
    for papel in ("gestor", "solicitante", "outro", "n1", "n2"):
        valores.extend(
            [
                {
                    "key": papel + "_email",
                    "value": papel + "@demo.helpdesk.example",
                    "enabled": True,
                    "type": "default",
                },
                {"key": papel + "_password", "value": "", "enabled": True, "type": "secret"},
            ]
        )
    (DESTINO / "local.example.postman_environment.json").write_text(
        json.dumps(
            {
                "name": "Help Desk - exemplo SEM credenciais",
                "values": valores,
                "_postman_variable_scope": "environment",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
