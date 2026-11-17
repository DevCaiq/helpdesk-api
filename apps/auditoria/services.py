from ipaddress import ip_address

from .models import LogAuditoria

USER_FIELDS = ("email", "nome", "perfil", "nivel", "is_active")
ENTITY_FIELDS = {
    "usuario": USER_FIELDS,
    "chamado": (
        "status",
        "prioridade",
        "nivel_atual",
        "responsavel_id",
        "categoria_id",
        "comentario_id",
        "interno",
        "triado_por_id",
        "evento_id",
        "prazo_resolucao",
        "alerta_id",
        "tipo",
    ),
    "categoria": ("nome", "ativa"),
    "politica_sla": ("prioridade", "minutos_resolucao"),
}


def usuario_snapshot(usuario):
    return {field: getattr(usuario, field) for field in USER_FIELDS}


def registrar_evento(
    *, acao, ator=None, entidade="usuario", entidade_id=None, antes=None, depois=None, request=None
):
    ip = request.META.get("REMOTE_ADDR") if request else None
    try:
        ip = str(ip_address(ip)) if ip else None
    except ValueError:
        ip = None
    return LogAuditoria.objects.create(
        acao=acao,
        ator=ator,
        entidade=entidade,
        entidade_id=str(entidade_id) if entidade_id is not None else "",
        antes={k: v for k, v in (antes or {}).items() if k in ENTITY_FIELDS.get(entidade, ())},
        depois={k: v for k, v in (depois or {}).items() if k in ENTITY_FIELDS.get(entidade, ())},
        ip=ip,
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500] if request else "",
    )
