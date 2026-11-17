import time

from django.core.management.base import BaseCommand, CommandError

from apps.sla.automacao import verificar_sla


class Command(BaseCommand):
    help = "Verifica SLA, gera alertas, escala chamados triados e efetiva fechamentos."

    def add_arguments(self, parser):
        parser.add_argument("--continuo", action="store_true", help="Repete até Ctrl+C.")
        parser.add_argument(
            "--intervalo", type=int, default=300, help="Intervalo em segundos (padrão 300)."
        )

    def handle(self, *args, **options):
        if options["intervalo"] < 1:
            raise CommandError("Intervalo deve ser positivo.")
        try:
            while True:
                resultado = verificar_sla()
                self.stdout.write(
                    f"Alertas: {resultado['alertas']}; escalados: {resultado['escalados']}; "
                    f"fechados: {resultado['fechados']}"
                )
                if not options["continuo"]:
                    break
                time.sleep(options["intervalo"])
        except KeyboardInterrupt:
            self.stdout.write("Verificação encerrada.")
