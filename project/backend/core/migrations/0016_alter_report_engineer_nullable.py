from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_alter_ticket_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="report",
            name="engineer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reports",
                to="core.engineerprofile",
            ),
        ),
    ]
