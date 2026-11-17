from django.contrib import admin
from django.db.models import Q

from .models import Categoria, Chamado, Comentario, HistoricoStatus
from .selectors import visiveis


class ConsultaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Chamado)
class ChamadoAdmin(ConsultaAdmin):
    list_display = ("id", "titulo", "status", "prioridade", "nivel_atual", "responsavel")
    list_filter = ("status", "prioridade", "nivel_atual")
    search_fields = ("titulo",)

    def get_queryset(self, request):
        return visiveis(request.user)


@admin.register(Comentario)
class ComentarioAdmin(ConsultaAdmin):
    def get_queryset(self, request):
        chamados = visiveis(request.user).values_list("pk", flat=True)
        return (
            super()
            .get_queryset(request)
            .filter(chamado_id__in=chamados)
            .exclude(Q(chamado__solicitante=request.user) & Q(interno=True))
        )


@admin.register(HistoricoStatus)
class HistoricoAdmin(ConsultaAdmin):
    def get_queryset(self, request):
        chamados = visiveis(request.user).values_list("pk", flat=True)
        return super().get_queryset(request).filter(chamado_id__in=chamados)


admin.site.register(Categoria, ConsultaAdmin)
