from datetime import timedelta

from apps.chamados import services
from apps.chamados.services_categorias import salvar_categoria
from apps.chamados.services_escalonamento import escalar_chamado, triar_chamado


def criar_cenarios(contas, referencia):
    # Dependência apenas de desenvolvimento, após o bloqueio explícito do seed em produção.
    from freezegun import freeze_time

    gestor, n1 = contas["gestor"], contas["n1"]
    with freeze_time(referencia - timedelta(days=7) + timedelta(minutes=1)):
        categorias = {
            key: salvar_categoria(ator=gestor, dados={"nome": nome})
            for key, nome in {"acesso": "Demo - Acesso", "infra": "Demo - Infraestrutura"}.items()
        }
    ids = {}
    config = [
        ("aberto", 10, "aberto"),
        ("atendimento", 120, "atendimento"),
        ("aguardando", 180, "aguardando"),
        ("fila_n2", 60, "n2"),
        ("resolvido", 120, "resolvido"),
        ("fechado", 5760, "fechado"),
        ("cancelado", 4320, "cancelado"),
        ("reaberto", 120, "reaberto"),
        ("critico_triado", 11, "critico_triado"),
        ("critico_sem_triagem", 11, "aberto"),
        ("outro", 5, "outro"),
    ]
    for key, minutos, estado in config:
        inicio = referencia - timedelta(minutes=minutos)
        critico = key.startswith("critico")
        ator = contas["outro"] if estado == "outro" else contas["solicitante"]
        with freeze_time(inicio):
            chamado = services.abrir_chamado(
                ator=ator,
                dados={
                    "titulo": f"[DEMO] {key.replace('_', ' ')}",
                    "descricao": "Cenário fictício de atendimento, sem dados reais.",
                    "categoria": categorias["infra" if critico else "acesso"],
                    "impacto": "ALTO" if critico else "MEDIO",
                    "urgencia": "ALTA" if critico else "MEDIA",
                },
            )
        ids[key] = chamado.pk
        if estado in ("aberto", "outro"):
            continue
        if estado == "critico_triado":
            with freeze_time(inicio + timedelta(minutes=1)):
                triar_chamado(
                    chamado_id=chamado.pk,
                    ator=n1,
                    motivo="Triagem N1 concluída para demonstração automática.",
                )
            continue
        if estado == "cancelado":
            with freeze_time(inicio + timedelta(minutes=2)):
                services.transicionar_chamado(
                    chamado_id=chamado.pk,
                    ator=ator,
                    status="CANCELADO",
                    motivo="Solicitação fictícia cancelada.",
                )
            continue
        with freeze_time(inicio + timedelta(minutes=5)):
            services.assumir_chamado(chamado_id=chamado.pk, ator=n1)
        if estado == "n2":
            with freeze_time(inicio + timedelta(minutes=6)):
                triar_chamado(
                    chamado_id=chamado.pk, ator=n1, motivo="Triagem indica necessidade de N2."
                )
            with freeze_time(inicio + timedelta(minutes=10)):
                escalar_chamado(
                    chamado_id=chamado.pk,
                    ator=n1,
                    motivo="Encaminhamento fictício para especialista N2.",
                )
            continue
        with freeze_time(inicio + timedelta(minutes=15)):
            services.comentar(
                chamado_id=chamado.pk, ator=n1, texto="Atendimento iniciado pela equipe."
            )
        if estado == "atendimento":
            with freeze_time(inicio + timedelta(minutes=20)):
                services.comentar(
                    chamado_id=chamado.pk,
                    ator=n1,
                    texto="Nota interna de demonstração, exclusiva da equipe.",
                    interno=True,
                )
        elif estado == "aguardando":
            with freeze_time(inicio + timedelta(minutes=20)):
                services.transicionar_chamado(
                    chamado_id=chamado.pk,
                    ator=n1,
                    status="AGUARDANDO_SOLICITANTE",
                    motivo="Informe o código do erro fictício.",
                )
        elif estado in ("resolvido", "fechado", "reaberto"):
            with freeze_time(inicio + timedelta(minutes=30)):
                services.transicionar_chamado(
                    chamado_id=chamado.pk,
                    ator=n1,
                    status="RESOLVIDO",
                    motivo="Solução de demonstração aplicada.",
                )
            if estado == "reaberto":
                with freeze_time(inicio + timedelta(minutes=40)):
                    services.reabrir_chamado(
                        chamado_id=chamado.pk, ator=ator, motivo="Falha fictícia retornou."
                    )
            elif estado == "fechado":
                fechamento = inicio + timedelta(days=3)
                with freeze_time(fechamento):
                    services.fechar_por_prazo(chamado.pk, fechamento)
    return {"categorias": {key: value.pk for key, value in categorias.items()}, "chamados": ids}
