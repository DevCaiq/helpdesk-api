from django.db.models import Prefetch, Q

from apps.sla.indicadores import ciclos_com_pausa

from .models import Chamado


def visiveis(usuario):
    qs = Chamado.objects.select_related("solicitante", "responsavel", "categoria").prefetch_related(
        Prefetch("ciclos", queryset=ciclos_com_pausa())
    )
    if not usuario.is_authenticated or not usuario.is_active:
        return qs.none()
    if usuario.perfil == "GESTOR":
        return qs
    if usuario.perfil == "ANALISTA":
        return qs.filter(
            Q(solicitante=usuario) | Q(nivel_atual=usuario.nivel) | Q(responsavel=usuario)
        )
    return qs.filter(solicitante=usuario)
