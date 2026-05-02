from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0004_alter_subscriptionplan_apple_product_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionplan",
            name="max_regenerations_per_month",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="usersubscription",
            name="regenerations_used_this_month",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
