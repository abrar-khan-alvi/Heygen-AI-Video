"""
Sync avatars from HeyGen API into CachedAvatar table.

Usage:
    python manage.py sync_avatars          # Sync all
    python manage.py sync_avatars --clear  # Clear + re-sync
"""

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from videogen.models import CachedAvatar


OUTFIT_KEYWORDS = {
    "business": ["office", "suit", "blazer", "formal", "business", "professional"],
    "casual": ["casual", "tshirt", "t-shirt", "hoodie", "jeans", "sweater", "relaxed"],
    "formal": ["formal", "suit", "dress", "gown", "tuxedo", "elegant", "graceful"],
    "healthcare": ["healthcare", "medical", "scrubs", "lab", "doctor", "nurse", "hospital"],
    "outdoor": ["outdoor", "sporty", "jacket", "adventure", "nature", "athletic"],
}

POSE_SCORES = {"standing": 2, "sitting": 1}
ANGLE_SCORES = {"front": 2, "side": 1}


def _parse_avatar_info(avatar):
    aid = avatar.get("avatar_id", "")
    aname = avatar.get("avatar_name", "")

    if len(aid) == 32 and "-" not in aid and "_" not in aid:
        return {"name": aname.split()[0] if aname else "Unknown", "pose": "", "outfit_raw": "", "angle": ""}

    if "_" in aid:
        parts = aid.split("_")
        if len(parts) >= 4:
            return {"name": parts[0], "pose": parts[1], "outfit_raw": "_".join(parts[2:-1]), "angle": parts[-1]}
        elif len(parts) == 3:
            return {"name": parts[0], "pose": parts[1], "outfit_raw": parts[2], "angle": ""}
        return {"name": parts[0], "pose": "", "outfit_raw": "", "angle": ""}

    if "-" in aid:
        parts = aid.split("-")
        return {"name": parts[0], "pose": "", "outfit_raw": "-".join(parts[1:-1]) if len(parts) > 2 else (parts[1] if len(parts) > 1 else ""), "angle": ""}

    return {"name": aname.split()[0] if aname else aid[:20], "pose": "", "outfit_raw": "", "angle": ""}


def _detect_outfit_category(avatar, parsed):
    search_text = " ".join([
        avatar.get("avatar_id", ""),
        avatar.get("avatar_name", ""),
        parsed.get("outfit_raw", ""),
    ]).lower()

    for category, keywords in OUTFIT_KEYWORDS.items():
        if any(kw in search_text for kw in keywords):
            return category
    return "business"



def _score_avatar(parsed):
    return POSE_SCORES.get(parsed.get("pose", "").lower(), 0) + ANGLE_SCORES.get(parsed.get("angle", "").lower(), 0)


class Command(BaseCommand):
    help = "Sync avatars from HeyGen API into local database"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear all before syncing")

    def handle(self, *args, **options):
        api_key = settings.HEYGEN_API_KEY
        if not api_key:
            self.stderr.write(self.style.ERROR("HEYGEN_API_KEY not set"))
            return

        if options["clear"]:
            deleted, _ = CachedAvatar.objects.all().delete()
            self.stdout.write(f"Cleared {deleted} existing avatars")

        self.stdout.write("Fetching avatars from HeyGen...")
        try:
            resp = requests.get(
                "https://api.heygen.com/v2/avatars",
                headers={"X-Api-Key": api_key, "Accept": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
            avatars = resp.json().get("data", {}).get("avatars", [])
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to fetch: {e}"))
            return

        self.stdout.write(f"Found {len(avatars)} avatars")

        # Deduplicate: best variant per name+gender+category
        best = {}
        for avatar in avatars:
            parsed = _parse_avatar_info(avatar)
            gender = avatar.get("gender", "").lower()
            if gender not in ("male", "female"):
                continue

            category = _detect_outfit_category(avatar, parsed)
            key = f"{parsed['name'].lower()}_{gender}_{category}"
            score = _score_avatar(parsed)

            # Try to pick a default voice if HeyGen didn't provide one
            default_voice_id = avatar.get("default_voice_id", "")
            if not default_voice_id:
                from videogen.models import CachedVoice
                # 1. Exact name match
                match = CachedVoice.objects.filter(
                    name__iexact=parsed["name"],
                    gender=gender,
                    is_active=True
                ).first()
                # 2. Fallback to first English voice
                if not match:
                    match = CachedVoice.objects.filter(
                        language_code__istartswith="en",
                        gender=gender,
                        is_active=True
                    ).first()
                
                if match:
                    default_voice_id = match.voice_id

            current = best.get(key)
            if not current or score > current["_score"]:
                best[key] = {
                    "avatar_id": avatar.get("avatar_id", ""),
                    "avatar_name": parsed["name"],
                    "gender": gender,
                    "outfit_category": category,
                    "pose": parsed.get("pose", ""),
                    "angle": parsed.get("angle", ""),
                    "preview_image_url": avatar.get("preview_image_url", ""),
                    "preview_video_url": avatar.get("preview_video_url", ""),
                    "default_voice_id": default_voice_id,
                    "_score": score,
                }

        created_count = 0
        updated_count = 0
        for data in best.values():
            data.pop("_score", None)
            _, created = CachedAvatar.objects.update_or_create(
                avatar_id=data["avatar_id"], defaults=data,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"\n✅ Sync: {created_count} created, {updated_count} updated"))

        self.stdout.write("\n--- By category ---")
        for cat in CachedAvatar.OutfitCategory.values:
            m = CachedAvatar.objects.filter(outfit_category=cat, gender="male", is_active=True).count()
            f = CachedAvatar.objects.filter(outfit_category=cat, gender="female", is_active=True).count()
            self.stdout.write(f"  {cat:12s} → male: {m}, female: {f}")
        self.stdout.write(f"\n  Total: {CachedAvatar.objects.filter(is_active=True).count()}")
