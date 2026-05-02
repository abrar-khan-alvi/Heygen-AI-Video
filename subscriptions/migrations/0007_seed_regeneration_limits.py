from django.db import migrations


LIMITS = {
    "free_trial": 1,
    "starter":    2,
    "pro":        4,
}


def set_regeneration_limits(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")
    for plan_type, limit in LIMITS.items():
        SubscriptionPlan.objects.filter(plan_type=plan_type).update(
            max_regenerations_per_month=limit
        )


def reverse_regeneration_limits(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")
    SubscriptionPlan.objects.all().update(max_regenerations_per_month=0)


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0006_usersubscription_trial_regenerations_used"),
    ]

    operations = [
        migrations.RunPython(set_regeneration_limits, reverse_regeneration_limits),
    ]
