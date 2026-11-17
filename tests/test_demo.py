import io
import json

import pytest
from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

pytestmark = pytest.mark.django_db


@pytest.fixture
def ambiente(tmp_path):
    return tmp_path / "local.postman_environment.json"


def seed(ambiente, **kwargs):
    output = io.StringIO()
    call_command("seed_demo", ambiente=str(ambiente), stdout=output, **kwargs)
    return output.getvalue()


def variaveis(ambiente):
    return {
        x["key"]: x["value"] for x in json.loads(ambiente.read_text(encoding="utf-8"))["values"]
    }


def test_seed_cria_cenarios_e_credenciais_privadas(ambiente):
    output = seed(ambiente)
    dados = variaveis(ambiente)
    user_model = apps.get_model("usuarios", "Usuario")
    assert user_model.objects.count() == 5
    assert not user_model.objects.filter(is_staff=True).exists()
    assert not user_model.objects.filter(is_superuser=True).exists()
    for papel in ("solicitante", "outro", "n1", "n2", "gestor"):
        user = user_model.objects.get(email=dados[f"{papel}_email"])
        assert user.check_password(dados[f"{papel}_password"])
        assert dados[f"{papel}_password"] not in output
    model = apps.get_model("chamados", "Chamado")
    assert model.objects.count() == 11
    assert model.objects.get(pk=dados["demo_fechado_id"]).status == "FECHADO"
    assert model.objects.get(pk=dados["demo_aguardando_id"]).ciclos.get().pausas.get().fim is None
    assert model.objects.get(pk=dados["demo_fila_n2_id"]).nivel_atual == "N2"
    critico = model.objects.get(pk=dados["demo_critico_triado_id"])
    assert critico.nivel_atual == "N1" and critico.triado_em is not None
    assert critico.aberto_em < timezone.now()
    manifesto = apps.get_model("demo", "DemoDataset").objects.get()
    serialized = json.dumps(manifesto.dados)
    assert "password" not in serialized and "access" not in serialized


def test_reexecucao_preserva_dados_e_senhas(ambiente):
    seed(ambiente)
    antes = ambiente.read_bytes()
    dados = variaveis(ambiente)
    user = apps.get_model("usuarios", "Usuario").objects.get(email=dados["gestor_email"])
    senha_hash = user.password
    chamado = apps.get_model("chamados", "Chamado").objects.get(pk=dados["demo_aberto_id"])
    chamado.titulo = "Alterado pelo usuário"
    chamado.save()
    logs = apps.get_model("auditoria", "LogAuditoria").objects.count()
    seed(ambiente)
    user.refresh_from_db()
    chamado.refresh_from_db()
    assert user.password == senha_hash
    assert chamado.titulo == "Alterado pelo usuário"
    assert ambiente.read_bytes() == antes
    assert apps.get_model("auditoria", "LogAuditoria").objects.count() == logs


def test_colisao_nao_altera_conta_existente(ambiente, usuario_factory):
    user = usuario_factory(email="gestor@demo.helpdesk.example")
    senha = user.password
    with pytest.raises(CommandError):
        seed(ambiente)
    user.refresh_from_db()
    assert user.password == senha and user.perfil == "SOLICITANTE"
    assert apps.get_model("usuarios", "Usuario").objects.count() == 1
    assert not apps.get_model("chamados", "Chamado").objects.exists()
    assert not ambiente.exists()


def test_seed_desabilitado_na_producao(ambiente, settings):
    settings.ALLOW_DEMO_SEED = False
    with pytest.raises(CommandError, match="desabilitado"):
        seed(ambiente)
    assert not apps.get_model("usuarios", "Usuario").objects.exists()


def test_rotacao_explicita_so_altera_senhas_do_demo(ambiente, usuario_factory):
    alheio = usuario_factory()
    hash_alheio = alheio.password
    seed(ambiente)
    antes = variaveis(ambiente)
    seed(ambiente, rotacionar_senhas=True)
    depois = variaveis(ambiente)
    assert antes["gestor_password"] != depois["gestor_password"]
    assert antes["demo_aberto_id"] == depois["demo_aberto_id"]
    alheio.refresh_from_db()
    assert alheio.password == hash_alheio
    assert apps.get_model("chamados", "Chamado").objects.count() == 11


def test_exportacao_falha_reverte_seed(ambiente, monkeypatch):
    from apps.demo import services

    def falha(*args, **kwargs):
        raise OSError("Sem espaço")

    monkeypatch.setattr(services, "exportar_ambiente", falha)
    with pytest.raises(CommandError):
        seed(ambiente)
    assert not apps.get_model("usuarios", "Usuario").objects.exists()
    assert not apps.get_model("demo", "DemoDataset").objects.exists()


def test_nao_sobrescreve_artefato_desconhecido(ambiente):
    ambiente.write_text("arquivo pessoal", encoding="utf-8")
    with pytest.raises(CommandError):
        seed(ambiente)
    assert ambiente.read_text(encoding="utf-8") == "arquivo pessoal"
    assert not apps.get_model("usuarios", "Usuario").objects.exists()


def test_senha_de_ambiente_fraca_rejeitada_sem_efeitos(ambiente, monkeypatch):
    monkeypatch.setenv("DEMO_PASSWORD", "123")
    with pytest.raises(CommandError):
        seed(ambiente)
    assert not apps.get_model("usuarios", "Usuario").objects.exists()


def test_manifesto_invalido_nao_redefine_conta_alheia(ambiente, usuario_factory):
    seed(ambiente)
    alheio = usuario_factory()
    senha = alheio.password
    manifesto = apps.get_model("demo", "DemoDataset").objects.get()
    manifesto.dados["usuarios"]["gestor"] = alheio.pk
    manifesto.save()
    with pytest.raises(CommandError):
        seed(ambiente, rotacionar_senhas=True)
    alheio.refresh_from_db()
    assert alheio.password == senha


def test_demo_automatico_sem_alterar_chamados_reais(ambiente, api):
    seed(ambiente)
    dados = variaveis(ambiente)
    call_command("verificar_sla", stdout=io.StringIO())
    model = apps.get_model("chamados", "Chamado")
    assert model.objects.get(pk=dados["demo_critico_triado_id"]).nivel_atual == "N2"
    assert model.objects.get(pk=dados["demo_critico_sem_triagem_id"]).nivel_atual == "N1"
    login = api.post(
        "/api/v1/auth/login/",
        {"email": dados["solicitante_email"], "password": dados["solicitante_password"]},
        format="json",
    )
    assert login.status_code == 200
    api.credentials(HTTP_AUTHORIZATION="Bearer " + login.data["access"])
    assert api.get(f"/api/v1/chamados/{dados['demo_outro_id']}/").status_code == 404


def test_falha_apos_publicar_arquivo_remove_artefato_sem_dataset(ambiente, monkeypatch):
    from apps.demo import services

    original = services.exportar_ambiente

    def falha(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("Falha após publicação")

    monkeypatch.setattr(services, "exportar_ambiente", falha)
    with pytest.raises(CommandError):
        seed(ambiente)
    assert not ambiente.exists()
    assert not apps.get_model("demo", "DemoDataset").objects.exists()


def test_falha_rotacao_restaura_arquivo_e_senhas(ambiente, monkeypatch):
    from apps.demo import services

    seed(ambiente)
    anterior = ambiente.read_bytes()
    user = apps.get_model("usuarios", "Usuario").objects.get(
        email=variaveis(ambiente)["gestor_email"]
    )
    senha = user.password
    original = services.exportar_ambiente

    def falha(*args, **kwargs):
        original(*args, **kwargs)
        raise OSError("Falha após publicação")

    monkeypatch.setattr(services, "exportar_ambiente", falha)
    with pytest.raises(CommandError):
        seed(ambiente, rotacionar_senhas=True)
    user.refresh_from_db()
    assert user.password == senha
    assert ambiente.read_bytes() == anterior


def test_criacao_de_atores_e_categorias_precede_chamados_historicos(ambiente):
    seed(ambiente)
    primeiro = apps.get_model("chamados", "Chamado").objects.order_by("aberto_em").first()
    logs = apps.get_model("auditoria", "LogAuditoria")
    for acao in ("DEMO_GESTOR_CRIADO", "USUARIO_CRIADO", "CATEGORIA_CRIADA"):
        assert logs.objects.filter(acao=acao).latest("criado_em").criado_em <= primeiro.aberto_em


def test_ambiente_ausente_exige_rotacao_explicita(ambiente):
    seed(ambiente)
    ambiente.unlink()
    with pytest.raises(CommandError):
        seed(ambiente)
    seed(ambiente, rotacionar_senhas=True)
    assert ambiente.is_file()
    assert apps.get_model("usuarios", "Usuario").objects.count() == 5


def test_rotacao_recusa_conta_que_recebeu_acesso_admin(ambiente):
    seed(ambiente)
    user = apps.get_model("usuarios", "Usuario").objects.get(
        email=variaveis(ambiente)["gestor_email"]
    )
    user.is_staff = True
    user.save()
    anterior = ambiente.read_bytes()
    with pytest.raises(CommandError):
        seed(ambiente, rotacionar_senhas=True)
    assert ambiente.read_bytes() == anterior


@pytest.mark.parametrize("tipo", ["categoria", "usuario"])
def test_colisao_independente_de_maiusculas_aborta_sem_alteracoes(ambiente, tipo):
    usuarios = apps.get_model("usuarios", "Usuario")
    categorias = apps.get_model("chamados", "Categoria")
    if tipo == "categoria":
        categorias.objects.create(nome="demo - acesso")
    else:
        usuarios.objects.create(email="GESTOR@DEMO.HELPDESK.EXAMPLE")
    antes = (usuarios.objects.count(), categorias.objects.count())
    with pytest.raises(CommandError):
        seed(ambiente)
    assert (usuarios.objects.count(), categorias.objects.count()) == antes
    assert not apps.get_model("chamados", "Chamado").objects.exists()
    assert not apps.get_model("demo", "DemoDataset").objects.exists()


@pytest.mark.parametrize("nome", ["segredos.json", "local.example.postman_environment.json"])
def test_exportacao_exige_nome_privado_coberto_por_gitignore(tmp_path, nome):
    with pytest.raises(CommandError):
        seed(tmp_path / nome)
    assert not apps.get_model("demo", "DemoDataset").objects.exists()


def test_seed_nao_executa_automacao_sobre_chamados_alheios(ambiente, api, equipe, abrir):
    from datetime import timedelta

    from freezegun import freeze_time

    from tests.helpers import action

    with freeze_time(timezone.now() - timedelta(minutes=20)):
        real = abrir(impacto="ALTO", urgencia="ALTA")
        assert (
            action(api, equipe, real, "triar", {"motivo": "Triagem real fora do demo"}).status_code
            == 200
        )
    seed(ambiente)
    chamado = apps.get_model("chamados", "Chamado").objects.get(pk=real["id"])
    assert chamado.nivel_atual == "N1"
    assert not chamado.eventos.filter(tipo="ESCALADO").exists()
