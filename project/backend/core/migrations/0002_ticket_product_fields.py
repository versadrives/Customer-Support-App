from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="model",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="ticket",
            name="serial_number",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="ticket",
            name="mfg_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
