from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_add_report_photos"),
    ]

    operations = [
        migrations.CreateModel(
            name="IssueOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ("name",),
            },
        ),
        migrations.AddField(
            model_name="ticket",
            name="service_type",
            field=models.CharField(
                choices=[("ONSITE", "Onsite"), ("REPLACEMENT", "Replacement")],
                default="ONSITE",
                max_length=20,
            ),
        ),
    ]
