from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from subscriptions.models import SubscriptionPlan, UserSubscription

User = get_user_model()


class Command(BaseCommand):
    help = "Grant a user unlimited (test) subscription access."

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="Email of the user to activate.")

    def handle(self, *args, **options):
        email = options["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f"No user found with email: {email}")

        # Bump the Enterprise plan to effectively unlimited limits
        plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type=SubscriptionPlan.PlanType.ENTERPRISE,
            defaults={
                "name": "Enterprise",
                "price_monthly": "199.00",
                "description": "Unlimited access.",
            },
        )
        plan.max_videos_per_month = 99999
        plan.max_script_generations_per_month = 99999
        plan.max_video_duration_seconds = 99999
        plan.is_active = True
        plan.save()

        sub, created = UserSubscription.objects.update_or_create(
            user=user,
            defaults={
                "plan": plan,
                "status": UserSubscription.Status.ACTIVE,
                "videos_generated_this_month": 0,
                "scripts_generated_this_month": 0,
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"\n{action} subscription for {user.email}"))
        self.stdout.write(f"  Plan    : {sub.plan.name}")
        self.stdout.write(f"  Status  : {sub.status}")
        self.stdout.write(f"  Videos  : {sub.plan.max_videos_per_month}/mo")
        self.stdout.write(f"  Scripts : {sub.plan.max_script_generations_per_month}/mo")
        self.stdout.write(f"  Duration: {sub.plan.max_video_duration_seconds}s max\n")
