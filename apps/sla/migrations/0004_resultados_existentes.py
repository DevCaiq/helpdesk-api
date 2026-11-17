from datetime import timedelta

from django.db import migrations


def preencher_resultados(apps, schema_editor):
    alias = schema_editor.connection.alias
    chamado_model = apps.get_model("chamados", "Chamado")
    ciclo_model = apps.get_model("sla", "CicloResolucao")
    for chamado in (
        chamado_model.objects.using(alias).filter(primeira_resposta_resultado="").iterator()
    ):
        if chamado.primeira_resposta_em:
            fim = chamado.primeira_resposta_em
            resultado = "CUMPRIDO" if fim <= chamado.prazo_primeira_resposta else "VIOLADO"
        else:
            ciclo = (
                ciclo_model.objects.using(alias)
                .filter(chamado_id=chamado.pk, encerrado_em__isnull=False)
                .order_by("id")
                .first()
            )
            if ciclo is None:
                continue
            fim = ciclo.encerrado_em
            resultado = "NAO_APLICAVEL" if ciclo.resultado == "NAO_APLICAVEL" else "VIOLADO"
        chamado.primeira_resposta_finalizada_em = fim
        chamado.primeira_resposta_resultado = resultado
        chamado.save(
            using=alias,
            update_fields=["primeira_resposta_finalizada_em", "primeira_resposta_resultado"],
        )
    for ciclo in (
        ciclo_model.objects.using(alias)
        .filter(resultado="VIOLADO", violado_em__isnull=True)
        .iterator()
    ):
        ciclo.violado_em = ciclo.encerrado_em or ciclo.prazo + timedelta(microseconds=1)
        ciclo.save(using=alias, update_fields=["violado_em"])


class Migration(migrations.Migration):
    dependencies = [
        ("sla", "0003_cicloresolucao_violado_em_alertasla"),
        ("chamados", "0002_chamado_primeira_resposta_finalizada_em_and_more"),
    ]
    operations = [migrations.RunPython(preencher_resultados, migrations.RunPython.noop)]
