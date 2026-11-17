from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.demo.services import seed_demo


class Command(BaseCommand):
    help = "Cria demonstração local idempotente e ambiente Postman privado; não imprime senhas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ambiente",
            default=str(settings.BASE_DIR / ".demo" / "local.postman_environment.json"),
        )
        parser.add_argument(
            "--rotacionar-senhas",
            action="store_true",
            help="Redefine explicitamente somente senhas das contas do manifesto demo.",
        )

    def handle(self, *args, **options):
        try:
            resultado = seed_demo(
                ambiente=Path(options["ambiente"]), rotacionar=options["rotacionar_senhas"]
            )
        except (OSError, ImportError) as exc:
            raise CommandError(
                "Falha ao preparar demo/arquivo; verifique o caminho "
                "e execute uv sync com extras dev."
            ) from exc
        mensagem = "Demo criado" if resultado["criado"] else "Demo preservado"
        if options["rotacionar_senhas"]:
            mensagem += "; senhas rotacionadas explicitamente"
        self.stdout.write(f"{mensagem}. Ambiente privado: {resultado['ambiente']}")
