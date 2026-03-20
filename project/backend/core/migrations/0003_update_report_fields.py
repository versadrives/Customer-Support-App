from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_ticket_product_fields"),
    ]

    operations = [
        migrations.RemoveField(model_name="report", name="fault_observed"),
        migrations.RemoveField(model_name="report", name="root_cause"),
        migrations.RemoveField(model_name="report", name="remarks"),
        migrations.RemoveField(model_name="report", name="qr_code"),
        migrations.AddField(
            model_name="report",
            name="service_provider_code",
            field=models.CharField(default="", max_length=60),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="report",
            name="number_of_fans",
            field=models.PositiveIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="report",
            name="serial_number",
            field=models.CharField(default="", max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="report",
            name="problem_identified",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="report",
            name="pcb_board_number",
            field=models.CharField(default="", max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="report",
            name="comments",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="report",
            name="charges_collected",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="report",
            name="kms_driven",
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="report",
            name="is_customer_polite",
            field=models.BooleanField(default=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="report",
            name="difficult_to_attend",
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]
