from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_ticket_service_type_issueoption"),
    ]

    operations = [
        migrations.CreateModel(
            name="Replacement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(blank=True, max_length=150)),
                ("ref_date", models.DateField(blank=True, null=True)),
                ("client_ref_date", models.DateField(blank=True, null=True)),
                ("ref_number", models.CharField(blank=True, max_length=80)),
                ("custom_challan_number", models.CharField(blank=True, max_length=80)),
                ("client_ref_number", models.CharField(blank=True, max_length=80)),
                ("organization_name", models.CharField(blank=True, max_length=120)),
                ("contact_name", models.CharField(blank=True, max_length=120)),
                ("contact_phone", models.CharField(blank=True, max_length=30)),
                ("category", models.CharField(blank=True, max_length=120)),
                ("billing_city", models.CharField(blank=True, max_length=120)),
                ("billing_state", models.CharField(blank=True, max_length=120)),
                ("billing_country", models.CharField(blank=True, max_length=120)),
                ("billing_address", models.TextField(blank=True)),
                ("billing_postal_code", models.CharField(blank=True, max_length=20)),
                ("item_name", models.CharField(blank=True, max_length=150)),
                ("item_description", models.TextField(blank=True)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("currency", models.CharField(default="India, Rupees", max_length=40)),
                ("tax_mode", models.CharField(default="Group", max_length=40)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("READY", "Ready"), ("DISPATCHED", "Dispatched"), ("COMPLETED", "Completed")], default="DRAFT", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("ticket", models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="replacement", to="core.ticket")),
            ],
            options={
                "ordering": ("-updated_at", "-created_at"),
            },
        ),
    ]
