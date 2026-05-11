"""
Management command: rewatermark_trial_videos
Re-applies watermarks to all completed Free Trial videos that were
saved without branding (is_watermarked=False).

Usage:
    python manage.py rewatermark_trial_videos
    python manage.py rewatermark_trial_videos --dry-run
"""
import os
import requests
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Re-watermark all completed Free Trial videos that are missing their watermark."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without making changes.",
        )

    def handle(self, *args, **options):
        from videogen.models import VideoProject
        from videogen.services import watermark_service, heygen_service

        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made."))

        total_ok = 0
        total_err = 0

        # ── VideoGen projects ──────────────────────────────────────────────────
        self.stdout.write("\n=== VideoGen projects ===")
        projects = VideoProject.objects.filter(
            status="video_completed", is_watermarked=False
        ).select_related("user", "user__subscription", "user__subscription__plan")

        for p in projects:
            if not p.user.subscription.is_trial:
                continue
            self.stdout.write(f"  [{p.id}] heygen_video_id={p.heygen_video_id}")
            if dry_run:
                self.stdout.write("    → would re-watermark")
                continue
            try:
                result = heygen_service.get_video_status(p.heygen_video_id)
                if result.get("status") != "completed":
                    self.stdout.write(f"    ✗ HeyGen status: {result.get('status')} — skipping")
                    total_err += 1
                    continue

                url = result.get("video_url")
                if not url:
                    self.stdout.write("    ✗ No video_url — skipping")
                    total_err += 1
                    continue

                resp = requests.get(url, timeout=120)
                resp.raise_for_status()
                video_bytes = resp.content
                self.stdout.write(f"    Downloaded {len(video_bytes):,} bytes")

                final_filename = f"{p.id}_branded.mp4"
                wm_file = watermark_service.apply_watermark(video_bytes, final_filename)

                # Remove stale disk file
                rel = os.path.join("videos", p.created_at.strftime("%Y/%m"), final_filename)
                full = os.path.join(settings.MEDIA_ROOT, rel)
                if os.path.exists(full):
                    os.remove(full)
                if p.video_file:
                    try:
                        p.video_file.delete(save=False)
                    except Exception:
                        pass

                p.video_file.save(final_filename, wm_file, save=False)
                p.is_watermarked = True
                p.save(update_fields=["video_file", "is_watermarked"])
                self.stdout.write(self.style.SUCCESS(f"    ✓ Watermarked → {final_filename}"))
                total_ok += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"    ✗ Error: {e}"))
                total_err += 1

        self.stdout.write(
            f"\n{'DRY RUN complete' if dry_run else 'Done'}. "
            f"Success: {total_ok}, Errors: {total_err}"
        )
