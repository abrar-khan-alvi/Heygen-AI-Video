from rest_framework import serializers
from .models import ProductPromoProject


class ProductPromoProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPromoProject
        fields = "__all__"
        read_only_fields = ("id", "user", "status", "created_at", "updated_at")


class ProductPromoProjectListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPromoProject
        fields = (
            "id", "product_name", "product_description",
            "status", "background", "created_at",
        )


class PromoProjectCreateSerializer(serializers.Serializer):
    product_name = serializers.CharField(max_length=255)
    product_description = serializers.CharField()


class PromoProjectUpdateSerializer(serializers.Serializer):
    """Accepts any subset of these fields for a PATCH update."""
    product_name        = serializers.CharField(max_length=255, required=False)
    product_description = serializers.CharField(required=False)
    avatar_id           = serializers.CharField(max_length=255, required=False)
    avatar_name         = serializers.CharField(max_length=255, required=False)
    avatar_gender       = serializers.CharField(max_length=20, required=False)
    avatar_preview_url  = serializers.URLField(required=False)
    voice_id            = serializers.CharField(max_length=255, required=False)
    # Background name (e.g. "Modern Office") — resolved to description in the view
    background          = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class PromoScriptFinalizeSerializer(serializers.Serializer):
    finalized_script = serializers.CharField()
