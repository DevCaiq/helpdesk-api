from rest_framework.permissions import BasePermission


class IsGestor(BasePermission):
    message = "Esta ação exige perfil Gestor."

    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and request.user.is_active
            and request.user.perfil == "GESTOR"
        )
