from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id", "name", "plan_type", "price_monthly", "currency",
            "max_videos_per_month", "max_script_generations_per_month",
            "has_priority_processing", "has_watermark",
            "description", "apple_product_id", "google_product_id",
        ]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    videos_remaining = serializers.SerializerMethodField()
    scripts_remaining = serializers.SerializerMethodField()
    trial_exhausted = serializers.BooleanField(read_only=True)
    is_trial = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserSubscription
        fields = [
            "id", "plan", "status", "platform",
            "product_id", "transaction_id",
            "is_trial", "trial_videos_used", "trial_exhausted",
            "videos_generated_this_month", "scripts_generated_this_month",
            "videos_remaining", "scripts_remaining",
            "started_at", "expires_at",
        ]

    def get_videos_remaining(self, obj):
        if obj.plan.plan_type == SubscriptionPlan.PlanType.FREE_TRIAL:
            return max(0, obj.plan.max_videos_per_month - obj.trial_videos_used)
        obj.reset_usage_if_needed()
        return max(0, obj.plan.max_videos_per_month - obj.videos_generated_this_month)

    def get_scripts_remaining(self, obj):
        obj.reset_usage_if_needed()
        return max(0, obj.plan.max_script_generations_per_month - obj.scripts_generated_this_month)


class IAPPurchaseSerializer(serializers.Serializer):
    """
    Frontend sends this after a successful In-App Purchase.

    Apple:  {platform: "apple",  product_id, purchase_token (receipt), transaction_id}
    Google: {platform: "google", product_id, purchase_token, transaction_id (orderId)}
    """
    platform = serializers.ChoiceField(choices=["apple", "google"])
    product_id = serializers.CharField(max_length=255)
    purchase_token = serializers.CharField()
    transaction_id = serializers.CharField(max_length=500)