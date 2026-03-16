#!/bin/sh
# =============================================================================
# entrypoint.sh — runs on every "docker compose up" before the server starts
# =============================================================================
set -e

echo ""
echo "════════════════════════════════════════════════════"
echo " 🚀  Starting Django backend setup..."
echo "════════════════════════════════════════════════════"

# ── 1. Apply database migrations ──────────────────────────────────────────────
echo ""
echo "▶ Running migrations..."
python manage.py migrate --no-input

# ── 2. Seed Industries & Backgrounds ──────────────────────────────────────────
echo ""
echo "▶ Seeding industries & backgrounds..."
python manage.py seed_options

# ── 3. Seed Subscription Plans ────────────────────────────────────────────────
echo ""
echo "▶ Seeding subscription plans..."
python manage.py seed_plans

# ── 4. Sync Cached Avatars from HeyGen ────────────────────────────────────────
echo ""
echo "▶ Syncing avatars from HeyGen API..."
python manage.py sync_avatars || echo "⚠  Avatar sync failed (API key missing or network error) — skipping"

# ── 5. Sync Cached Voices from HeyGen ─────────────────────────────────────────
echo ""
echo "▶ Syncing voices from HeyGen API..."
python manage.py sync_voices || echo "⚠  Voice sync failed (API key missing or network error) — skipping"

echo ""
echo "════════════════════════════════════════════════════"
echo " ✅  Setup complete — starting server"
echo "════════════════════════════════════════════════════"
echo ""

# Hand off to the CMD defined in docker-compose (e.g. runserver / celery)
exec "$@"
