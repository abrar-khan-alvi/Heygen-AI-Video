"""
Sync voices from HeyGen API into CachedVoice table.

Usage:
    python manage.py sync_voices          # Sync all
    python manage.py sync_voices --clear  # Clear + re-sync
"""

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from videogen.models import CachedVoice


class Command(BaseCommand):
    help = "Sync voices from HeyGen API into local database"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear all before syncing")

    def handle(self, *args, **options):
        api_key = settings.HEYGEN_API_KEY
        if not api_key:
            self.stderr.write(self.style.ERROR("HEYGEN_API_KEY not set"))
            return

        if options["clear"]:
            deleted, _ = CachedVoice.objects.all().delete()
            self.stdout.write(f"Cleared {deleted} existing voices")

        self.stdout.write("Fetching voices from HeyGen...")
        try:
            resp = requests.get(
                "https://api.heygen.com/v2/voices",
                headers={"X-Api-Key": api_key, "Accept": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
            voices = resp.json().get("data", {}).get("voices", [])
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to fetch voices: {e}"))
            return

        self.stdout.write(f"Found {len(voices)} voices")

        created_count = 0
        updated_count = 0

        for voice in voices:
            voice_id = voice.get("voice_id", "").strip()
            if not voice_id:
                continue

            data = {
                "name": voice.get("name", "") or "",
                "language": voice.get("language", "") or "",
                "language_code": voice.get("language_code", "") or "",
                "gender": (voice.get("gender", "") or "").lower(),
                "preview_audio_url": voice.get("preview_audio_url", "") or "",
            }

            _, created = CachedVoice.objects.update_or_create(
                voice_id=voice_id, defaults=data,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Sync: {created_count} created, {updated_count} updated")
        )

        self.stdout.write("\n--- By language (top 10) ---")
        from django.db.models import Count
        top_langs = (
            CachedVoice.objects.filter(is_active=True)
            .values("language")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        for row in top_langs:
            self.stdout.write(f"  {row['language'] or '(unknown)':30s} → {row['count']}")
        self.stdout.write(f"\n  Total: {CachedVoice.objects.filter(is_active=True).count()}")
