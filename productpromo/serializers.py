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
        fields = ("id", "product_name", "status", "created_at")

class PromoProjectCreateSerializer(serializers.Serializer):
    product_name = serializers.CharField(max_length=255)
    product_description = serializers.CharField()

class PromoProjectUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPromoProject
        fields = ("avatar_id", "avatar_name", "avatar_gender", "avatar_preview_url", "voice_id")

class PromoScriptFinalizeSerializer(serializers.Serializer):
    finalized_script = serializers.CharField()
