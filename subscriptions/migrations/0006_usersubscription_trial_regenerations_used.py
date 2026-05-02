from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0005_subscriptionplan_max_regenerations_per_month_usersubscription_regenerations_used_this_month"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersubscription",
            name="trial_regenerations_used",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
