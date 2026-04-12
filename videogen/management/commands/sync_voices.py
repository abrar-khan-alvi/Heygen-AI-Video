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

        self.stdout.write("Fetching Starfish-compatible voices from HeyGen...")
        
        total_created = 0
        total_updated = 0
        next_token = None
        record_limit = 2000  # Safety limit to avoid infinite loops or excessive data
        total_fetched = 0
        
        while total_fetched < record_limit:
            params = {}
            if next_token:
                params["token"] = next_token
                
            try:
                resp = requests.get(
                    "https://api.heygen.com/v1/audio/voices",
                    headers={"X-Api-Key": api_key, "Accept": "application/json"},
                    params=params,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                
                page_voices = data.get("data", [])
                if not isinstance(page_voices, list):
                    break
                
                for voice in page_voices:
                    voice_id = voice.get("voice_id", "").strip()
                    if not voice_id:
                        continue

                    # Map language to en/other basic code if needed
                    language = voice.get("language", "") or ""
                    lang_code = "en" if "english" in language.lower() else ""
                    
                    data_dict = {
                        "name": voice.get("name", "") or "",
                        "language": language,
                        "language_code": lang_code,
                        "gender": (voice.get("gender", "") or "").lower(),
                        "preview_audio_url": voice.get("preview_audio_url", "") or "",
                    }

                    _, created = CachedVoice.objects.update_or_create(
                        voice_id=voice_id, defaults=data_dict,
                    )
                    if created:
                        total_created += 1
                    else:
                        total_updated += 1
                
                total_fetched += len(page_voices)
                next_token = data.get("next_token")
                
                self.stdout.write(f"  ... synced {total_fetched} voices (Created: {total_created}, Updated: {total_updated})")
                
                if not next_token:
                    break
                    
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed during sync: {e}"))
                break

        self.stdout.write(self.style.SUCCESS(f"\n✅ Sync Complete: {total_created} created, {total_updated} updated"))

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
