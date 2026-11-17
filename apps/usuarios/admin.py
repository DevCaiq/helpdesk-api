from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import UsuarioChangeForm, UsuarioCreationForm
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm
    list_display = ("email", "nome", "perfil", "nivel", "is_active")
    list_filter = ("perfil", "nivel", "is_active", "is_staff")
    ordering = ("email",)
    search_fields = ("email", "nome")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Perfil", {"fields": ("nome", "perfil", "nivel")}),
        (
            "Permissões",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "nome",
                    "perfil",
                    "nivel",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
