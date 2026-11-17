from django.contrib import admin

from .models import LogAuditoria


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "acao", "ator", "entidade_id")
    list_filter = ("acao",)
    readonly_fields = (
        "ator",
        "acao",
        "entidade",
        "entidade_id",
        "antes",
        "depois",
        "ip",
        "user_agent",
        "criado_em",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
