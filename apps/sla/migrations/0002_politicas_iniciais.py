from django.db import migrations


def criar_politicas(apps, schema_editor):
    model = apps.get_model("sla", "PoliticaSLA")
    for prioridade, minutos in {"CRITICA": 240, "ALTA": 480, "MEDIA": 1440, "BAIXA": 4320}.items():
        model.objects.using(schema_editor.connection.alias).get_or_create(
            prioridade=prioridade, defaults={"minutos_resolucao": minutos}
        )


class Migration(migrations.Migration):
    dependencies = [("sla", "0001_initial")]
    operations = [migrations.RunPython(criar_politicas, migrations.RunPython.noop)]
