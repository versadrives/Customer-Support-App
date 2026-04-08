from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0003_update_report_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='report',
            name='number_of_fans',
        ),
    ]
