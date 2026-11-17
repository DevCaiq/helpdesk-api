from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (
    AcaoView,
    CategoriaViewSet,
    ChamadosView,
    ChamadoView,
    ComentariosView,
    EventosView,
    HistoricoView,
)

router = SimpleRouter()
router.register("categorias", CategoriaViewSet, basename="categoria")
urlpatterns = [
    path("", include(router.urls)),
    path("chamados/", ChamadosView.as_view(), name="chamados"),
    path("chamados/<int:pk>/", ChamadoView.as_view(), name="chamado"),
    path("chamados/<int:pk>/comentarios/", ComentariosView.as_view(), name="comentarios"),
    path("chamados/<int:pk>/historico/", HistoricoView.as_view(), name="historico"),
    path("chamados/<int:pk>/eventos/", EventosView.as_view(), name="eventos-chamado"),
    *[
        path(f"chamados/<int:pk>/{acao}/", AcaoView.as_view(operacao=acao), name=acao)
        for acao in (
            "assumir",
            "transicionar",
            "reabrir",
            "reatribuir",
            "triar",
            "escalar",
            "prioridade",
        )
    ],
]
