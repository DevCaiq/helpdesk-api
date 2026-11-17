from django.urls import path

from .auth_views import LoginView, LogoutView, RefreshView
from .views import AlterarUsuarioView, EquipeView, MeView, UsuariosView

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("usuarios/", UsuariosView.as_view(), name="usuarios"),
    path("usuarios/me/", MeView.as_view(), name="me"),
    path("usuarios/staff/", EquipeView.as_view(), name="equipe"),
    path("usuarios/<int:pk>/", AlterarUsuarioView.as_view(), name="alterar-usuario"),
]
