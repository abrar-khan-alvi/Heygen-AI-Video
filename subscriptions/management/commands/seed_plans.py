from django.core.management.base import BaseCommand
from subscriptions.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Seed subscription plans: Free Trial (3 videos), Starter (£7), Pro (£14)"

    def handle(self, *args, **options):
        plans = [
            {
                "name": "Free Trial",
                "plan_type": "free_trial",
                "price_monthly": 0,
                "currency": "GBP",
                "max_videos_per_month": 3,  # 3 LIFETIME total, not monthly
                "max_script_generations_per_month": 10,
                "has_priority_processing": False,
                "has_watermark": True,
                "description": (
                    "3 free video generations. No payment required. "
                    "Once used, subscribe to continue."
                ),
                "apple_product_id": "",
                "google_product_id": "",
            },
            {
                "name": "Starter",
                "plan_type": "starter",
                "price_monthly": 7,
                "currency": "GBP",
                "max_videos_per_month": 5,
                "max_script_generations_per_month": 15,
                "has_priority_processing": False,
                "has_watermark": False,
                "description": (
                    "5 video uploads per month. No watermark. "
                    "Standard export quality. £7/month."
                ),
                "apple_product_id": "com.yourapp.starter_monthly",
                "google_product_id": "starter_monthly",
            },
            {
                "name": "Pro",
                "plan_type": "pro",
                "price_monthly": 14,
                "currency": "GBP",
                "max_videos_per_month": 15,
                "max_script_generations_per_month": 50,
                "has_priority_processing": True,
                "has_watermark": False,
                "description": (
                    "15 video uploads per month. Priority processing. "
                    "Full access to all features. £14/month."
                ),
                "apple_product_id": "com.yourapp.pro_monthly",
                "google_product_id": "pro_monthly",
            },
        ]

        for plan_data in plans:
            obj, created = SubscriptionPlan.objects.update_or_create(
                plan_type=plan_data["plan_type"],
                defaults=plan_data,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  {action}: {obj.name}"))

        self.stdout.write(self.style.SUCCESS(
            "\nDone. Update apple/google product IDs in admin to match your store setup."
        ))