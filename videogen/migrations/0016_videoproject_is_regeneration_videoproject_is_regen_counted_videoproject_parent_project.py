from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("videogen", "0015_videoproject_is_counted"),
    ]

    operations = [
        migrations.AddField(
            model_name="videoproject",
            name="is_regeneration",
            field=models.BooleanField(
                default=False,
                help_text="True if this project was created by regenerating an existing completed video.",
            ),
        ),
        migrations.AddField(
            model_name="videoproject",
            name="is_regen_counted",
            field=models.BooleanField(
                default=False,
                help_text="True once the regeneration counter has been incremented (only for regenerations).",
            ),
        ),
        migrations.AddField(
            model_name="videoproject",
            name="parent_project",
            field=models.ForeignKey(
                blank=True,
                help_text="The original project this was regenerated from.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="regenerations",
                to="videogen.videoproject",
            ),
        ),
    ]
