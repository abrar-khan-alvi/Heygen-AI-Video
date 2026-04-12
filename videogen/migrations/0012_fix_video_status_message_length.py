# Generated manually to fix PostgreSQL varchar(200) error

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videogen', '0011_videoproject_is_watermarked'),
    ]

    operations = [
        migrations.AlterField(
            model_name='videoproject',
            name='video_status_message',
            field=models.TextField(blank=True, default=''),
        ),
    ]
