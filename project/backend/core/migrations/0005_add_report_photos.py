from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_remove_report_number_of_fans'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='before_service_photo',
            field=models.ImageField(blank=True, null=True, upload_to='reports/before/'),
        ),
        migrations.AddField(
            model_name='report',
            name='after_service_photo',
            field=models.ImageField(blank=True, null=True, upload_to='reports/after/'),
        ),
    ]
