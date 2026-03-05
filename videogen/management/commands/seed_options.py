"""
Seed default industries and backgrounds.
Usage: python manage.py seed_options
"""

from django.core.management.base import BaseCommand
from videogen.models import Industry, Background

INDUSTRIES = [
    {"name": "Digital Marketing", "icon": "megaphone"},
    {"name": "E-Commerce", "icon": "shopping-cart"},
    {"name": "Real Estate", "icon": "building"},
    {"name": "Travel & Tourism", "icon": "plane"},
    {"name": "Healthcare", "icon": "heart-pulse"},
    {"name": "Education", "icon": "graduation-cap"},
    {"name": "Finance & Banking", "icon": "wallet"},
    {"name": "Technology", "icon": "cpu"},
    {"name": "Food & Restaurant", "icon": "utensils"},
    {"name": "Fitness & Wellness", "icon": "dumbbell"},
    {"name": "Fashion & Beauty", "icon": "scissors"},
    {"name": "Automotive", "icon": "car"},
    {"name": "Legal Services", "icon": "scale"},
    {"name": "Entertainment", "icon": "film"},
    {"name": "SaaS / Software", "icon": "code"},
    {"name": "Non-Profit", "icon": "hand-heart"},
    {"name": "Construction", "icon": "hard-hat"},
    {"name": "Consulting", "icon": "briefcase"},
    {"name": "Other", "icon": "grid"},
]

BACKGROUNDS = [
    {"name": "Modern Office", "description": "A clean, modern glass office with ambient lighting", "icon": "building"},
    {"name": "City Skyline", "description": "City skyline at sunset with warm golden tones", "icon": "sunset"},
    {"name": "White Studio", "description": "Clean white studio background with soft lighting", "icon": "square"},
    {"name": "Nature Outdoor", "description": "Outdoor natural setting with greenery and soft sunlight", "icon": "tree"},
    {"name": "Coffee Shop", "description": "Cozy coffee shop interior with warm ambient lighting", "icon": "coffee"},
    {"name": "Classroom", "description": "Modern classroom or lecture hall setting", "icon": "book"},
    {"name": "Hospital", "description": "Clean hospital or medical clinic interior", "icon": "heart-pulse"},
    {"name": "Gym", "description": "Modern gym or fitness studio with equipment", "icon": "dumbbell"},
    {"name": "Tech Startup", "description": "Trendy tech startup office with open workspace", "icon": "cpu"},
    {"name": "Luxury Interior", "description": "Elegant luxury interior with sophisticated decor", "icon": "crown"},
    {"name": "Warehouse", "description": "Industrial warehouse or factory floor", "icon": "box"},
    {"name": "Rooftop", "description": "Rooftop terrace with panoramic city views", "icon": "sun"},
    {"name": "Library", "description": "Quiet library with bookshelves in the background", "icon": "book-open"},
    {"name": "Abstract Gradient", "description": "Smooth abstract gradient background with vibrant colors", "icon": "palette"},
    {"name": "Plain Color", "description": "Solid clean background color", "icon": "circle"},
]


class Command(BaseCommand):
    help = "Seed default industries and backgrounds"

    def handle(self, *args, **options):
        for i, data in enumerate(INDUSTRIES):
            _, created = Industry.objects.update_or_create(
                name=data["name"],
                defaults={"icon": data["icon"], "sort_order": i, "is_active": True},
            )
            self.stdout.write(f"  [{'CREATED' if created else 'exists'}] Industry: {data['name']}")

        for i, data in enumerate(BACKGROUNDS):
            _, created = Background.objects.update_or_create(
                name=data["name"],
                defaults={"description": data["description"], "icon": data["icon"], "sort_order": i, "is_active": True},
            )
            self.stdout.write(f"  [{'CREATED' if created else 'exists'}] Background: {data['name']}")

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Done: {Industry.objects.count()} industries, {Background.objects.count()} backgrounds"
        ))