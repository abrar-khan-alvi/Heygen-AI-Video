from django.contrib import admin
from .models import ProductPromoProject

@admin.register(ProductPromoProject)
class ProductPromoProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "product_name", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("product_name", "product_description", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")
