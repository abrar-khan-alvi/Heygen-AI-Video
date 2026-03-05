from django.db import models
from django.conf import settings
from django.utils import timezone


class SubscriptionPlan(models.Model):
    class PlanType(models.TextChoices):
        FREE_TRIAL = "free_trial", "Free Trial"
        STARTER = "starter", "Starter"
        PRO = "pro", "Pro"

    name = models.CharField(max_length=50, unique=True)
    plan_type = models.CharField(max_length=20, choices=PlanType.choices, unique=True)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    currency = models.CharField(max_length=5, default="GBP")

    # Limits
    max_videos_per_month = models.PositiveIntegerField(default=5)
    max_script_generations_per_month = models.PositiveIntegerField(default=10)
    has_priority_processing = models.BooleanField(default=False)
    has_watermark = models.BooleanField(default=False)

    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    # IAP product IDs
    apple_product_id = models.CharField(max_length=255, blank=True, db_index=True)
    google_product_id = models.CharField(max_length=255, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["price_monthly"]

    def __str__(self):
        return f"{self.name} ({self.currency} {self.price_monthly}/mo)"


class UserSubscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        TRIAL = "trial", "Free Trial"

    class Platform(models.TextChoices):
        APPLE = "apple", "Apple"
        GOOGLE = "google", "Google"
        NONE = "none", "None"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscribers",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRIAL,
        db_index=True,
    )

    # IAP fields
    platform = models.CharField(
        max_length=10, choices=Platform.choices, default=Platform.NONE,
    )
    transaction_id = models.CharField(
        max_length=500, blank=True, db_index=True,
    )
    purchase_token = models.TextField(blank=True)
    product_id = models.CharField(max_length=255, blank=True)

    # Usage tracking
    videos_generated_this_month = models.PositiveIntegerField(default=0)
    scripts_generated_this_month = models.PositiveIntegerField(default=0)
    usage_reset_date = models.DateField(default=timezone.now)

    # Free trial lifetime counter
    trial_videos_used = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            # Duplicate transaction check on verify-purchase
            models.Index(fields=["transaction_id"], name="idx_sub_transaction"),
        ]

    def __str__(self):
        return f"{self.user} — {self.plan.name} ({self.status})"

    # ── Usage reset (paid plans only) ───────────────────────────────────

    def reset_usage_if_needed(self):
        if self.plan.plan_type == SubscriptionPlan.PlanType.FREE_TRIAL:
            return

        today = timezone.now().date()
        if today.month != self.usage_reset_date.month or today.year != self.usage_reset_date.year:
            self.videos_generated_this_month = 0
            self.scripts_generated_this_month = 0
            self.usage_reset_date = today
            self.save(update_fields=[
                "videos_generated_this_month",
                "scripts_generated_this_month",
                "usage_reset_date",
            ])

    # ── Permission checks ───────────────────────────────────────────────

    def can_generate_video(self):
        if self.plan.plan_type == SubscriptionPlan.PlanType.FREE_TRIAL:
            return self.trial_videos_used < self.plan.max_videos_per_month
        self.reset_usage_if_needed()
        return self.videos_generated_this_month < self.plan.max_videos_per_month

    def can_generate_script(self):
        self.reset_usage_if_needed()
        return self.scripts_generated_this_month < self.plan.max_script_generations_per_month

    # ── Increment (only on SUCCESS) ─────────────────────────────────────

    def increment_video_count(self):
        if self.plan.plan_type == SubscriptionPlan.PlanType.FREE_TRIAL:
            self.trial_videos_used += 1
            self.save(update_fields=["trial_videos_used"])
        else:
            self.videos_generated_this_month += 1
            self.save(update_fields=["videos_generated_this_month"])

    def increment_script_count(self):
        self.scripts_generated_this_month += 1
        self.save(update_fields=["scripts_generated_this_month"])

    # ── Status checks ───────────────────────────────────────────────────

    @property
    def is_active_subscription(self):
        return self.status in [self.Status.ACTIVE, self.Status.TRIAL]

    @property
    def is_trial(self):
        return self.plan.plan_type == SubscriptionPlan.PlanType.FREE_TRIAL

    @property
    def trial_exhausted(self):
        if not self.is_trial:
            return False
        return self.trial_videos_used >= self.plan.max_videos_per_month