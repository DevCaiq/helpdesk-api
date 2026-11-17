from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.chamados.choices import Status
from apps.chamados.models import Chamado
from apps.chamados.services import fechar_por_prazo


class Command(BaseCommand):
    help = "Fecha chamados resolvidos elegíveis após 48h sem interação do solicitante."

    def handle(self, *args, **options):
        agora = timezone.now()
        ids = Chamado.objects.filter(status=Status.RESOLVIDO).values_list("pk", flat=True)
        count = 0
        for chamado_id in ids.iterator(chunk_size=200):
            count += fechar_por_prazo(chamado_id, agora)
        self.stdout.write(f"Chamados fechados: {count}")
