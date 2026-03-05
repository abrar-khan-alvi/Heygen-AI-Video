from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        "name", "plan_type", "price_monthly", "currency",
        "max_videos_per_month", "max_script_generations_per_month",
        "has_priority_processing", "has_watermark",
        "apple_product_id", "google_product_id", "is_active",
    ]
    list_filter = ["is_active", "plan_type"]
    fieldsets = (
        (None, {
            "fields": (
                "name", "plan_type", "price_monthly", "currency",
                "description", "is_active",
            ),
        }),
        ("Limits & Features", {
            "fields": (
                "max_videos_per_month", "max_script_generations_per_month",
                "has_priority_processing", "has_watermark",
            ),
        }),
        ("In-App Purchase Product IDs", {
            "fields": ("apple_product_id", "google_product_id"),
        }),
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "user", "plan", "status", "platform",
        "trial_videos_used",
        "videos_generated_this_month", "scripts_generated_this_month",
        "started_at",
    ]
    list_filter = ["status", "plan", "platform"]
    search_fields = ["user__email", "user__username", "transaction_id"]
    raw_id_fields = ["user"]
    readonly_fields = ["started_at"]
    fieldsets = (
        (None, {
            "fields": ("user", "plan", "status", "started_at", "expires_at"),
        }),
        ("In-App Purchase", {
            "fields": ("platform", "product_id", "transaction_id", "purchase_token"),
        }),
        ("Usage — Trial", {
            "fields": ("trial_videos_used",),
            "description": "Lifetime count for free trial (3 total, never resets).",
        }),
        ("Usage — Monthly (paid plans)", {
            "fields": (
                "videos_generated_this_month",
                "scripts_generated_this_month",
                "usage_reset_date",
            ),
        }),
    )