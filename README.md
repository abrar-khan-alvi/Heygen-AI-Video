# AI Video Backend

A **Django REST Framework** backend for an AI-powered video generation mobile app. Users describe their business, pick an avatar and background, get an AI-written script (via Gemini), and generate a professional talking-head video (via HeyGen) — all through a mobile-friendly API.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 4.2 + Django REST Framework |
| Auth | JWT (SimpleJWT) + Email OTP + Google/Apple OAuth |
| AI Script | Google Gemini API (`google-genai`) |
| Video Gen | HeyGen Video Agent API |
| Task Queue | Celery + Redis |
| Database | SQLite (dev) → PostgreSQL (prod recommended) |
| Container | Docker + Docker Compose |

---

## Project Structure

```
backendgen/
├── core/               # Django settings, root URLs, throttles
├── accounts/           # Auth: signup, OTP, login, social auth, profile
├── subscriptions/      # Plans, IAP (Apple/Google) purchase verification
├── videogen/           # Video projects, avatars, Gemini + HeyGen services
│   ├── models.py       # VideoProject, CachedAvatar, Industry, Background
│   ├── views.py        # All API views
│   ├── serializers.py
│   ├── services/
│   │   ├── gemini_service.py   # Script generation
│   │   └── heygen_service.py  # Video generation + status polling
│   └── management/commands/
│       ├── sync_avatars.py     # Sync HeyGen avatars → local DB
│       └── seed_options.py     # Seed industries + backgrounds
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Quick Start (Docker)

### 1. Clone & configure

```bash
git clone <repo-url>
cd backendgen
cp .env.example .env   # fill in your API keys (see below)
```

### 2. Start services

```bash
docker compose up --build
```

This starts three containers:
- **`web`** — Django dev server on `http://localhost:8000`
- **`worker`** — Celery task worker
- **`backend-redis`** — Redis broker on port `6379`

### 3. First-time setup

Run these once after the containers are up:

```bash
# Apply migrations
docker compose exec web python manage.py migrate

# Create an admin user
docker compose exec web python manage.py createsuperuser

# Seed industries and backgrounds
docker compose exec web python manage.py seed_options

# Seed subscription plans (Free Trial / Starter / Pro)
docker compose exec web python manage.py seed_plans

# Sync avatars from HeyGen into local DB (~289 avatars)
docker compose exec web python manage.py sync_avatars
```

### 4. Access

| URL | Description |
|---|---|
| `http://localhost:8000/admin/` | Django admin |
| `http://localhost:8000/api/v1/` | REST API base |

---

## Environment Variables

Create a `.env` file in the project root:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database
DB_DIR=/app/db

# Email (SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your@email.com

# OTP
OTP_EXPIRY_MINUTES=10

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id

# HeyGen
HEYGEN_API_KEY=your-heygen-api-key

# Gemini
GEMINI_API_KEY=your-gemini-api-key

# Celery
CELERY_BROKER_URL=redis://backend-redis:6379/0
CELERY_RESULT_BACKEND=redis://backend-redis:6379/1
```

---

## API Overview

**Base URL:** `http://localhost:8000/api/v1`  
**Auth header:** `Authorization: Bearer <access_token>`

### Authentication `/auth/`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/signup/` | — | Register (sends OTP) |
| POST | `/auth/verify-otp/` | — | Verify email OTP → creates account |
| POST | `/auth/resend-otp/` | — | Resend OTP |
| POST | `/auth/login/` | — | Login → returns JWT tokens |
| POST | `/auth/logout/` | ✅ | Blacklist refresh token |
| POST | `/auth/token/refresh/` | — | Refresh access token |
| POST | `/auth/forgot-password/` | — | Send reset OTP |
| POST | `/auth/verify-reset-otp/` | — | Verify reset OTP → returns token |
| POST | `/auth/reset-password/` | — | Set new password |
| POST | `/auth/change-password/` | ✅ | Change password (logged in) |
| GET/PATCH | `/auth/profile/` | ✅ | View / update profile |
| POST | `/auth/google/` | — | Google Sign In |
| POST | `/auth/apple/` | — | Apple Sign In |

### Subscriptions `/subscriptions/`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/subscriptions/plans/` | ✅ | List available plans |
| GET | `/subscriptions/me/` | ✅ | Current subscription & usage (auto-assigns free trial) |
| POST | `/subscriptions/verify-purchase/` | ✅ | Verify Apple/Google IAP → activate plan |
| POST | `/subscriptions/cancel/` | ✅ | Cancel subscription |

### Video Generation `/videogen/`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/videogen/options/industries/` | — | List industries |
| GET | `/videogen/options/backgrounds/` | — | List backgrounds |
| GET | `/videogen/options/avatars/` | — | 2 random avatars per category |
| GET | `/videogen/options/avatars/?category=business` | — | All avatars in category |
| GET | `/videogen/options/avatars/?category=casual&gender=female` | — | Filtered avatars |
| GET | `/videogen/options/avatars/<avatar_id>/` | — | Single avatar detail |
| POST | `/videogen/projects/create/` | ✅ | Screen 1 — create draft |
| PATCH | `/videogen/projects/<id>/update/` | ✅ | Screens 2–4 — update fields |
| POST | `/videogen/projects/<id>/generate-script/` | ✅ | Screen 5 — Gemini AI script |
| PUT | `/videogen/projects/<id>/finalize-script/` | ✅ | Screen 6 — approve script |
| POST | `/videogen/projects/<id>/generate-video/` | ✅ | Screen 7 — start HeyGen render |
| GET | `/videogen/projects/<id>/video-status/` | ✅ | Screen 8 — poll render status |
| GET | `/videogen/projects/` | ✅ | List all projects (cursor-paginated) |
| GET | `/videogen/projects/<id>/` | ✅ | Project detail |
| DELETE | `/videogen/projects/<id>/` | ✅ | Delete project |

---

## User Flow

```
SIGNUP → VERIFY OTP → LOGIN
    ↓
GET /subscriptions/me/  (auto-assigns Free Trial)
    ↓
GET /options/industries + backgrounds + avatars
    ↓
POST /projects/create/          (Screen 1: pick industry)
    ↓
PATCH /projects/<id>/update/    (Screen 2: title + description)
PATCH /projects/<id>/update/    (Screen 3: background)
PATCH /projects/<id>/update/    (Screen 4: avatar)
    ↓
POST /projects/<id>/generate-script/   (Screen 5: Gemini writes script)
    ↓
PUT  /projects/<id>/finalize-script/   (Screen 6: user edits & approves)
    ↓
POST /projects/<id>/generate-video/    (Screen 7: HeyGen starts rendering)
    ↓
GET  /projects/<id>/video-status/      (Screen 8: poll every 5–10s)
    ↓
video_completed ✅  →  video_file_url ready to play
```

---

## Subscription Plans

| Plan | Videos/month | Scripts/month | Watermark |
|---|---|---|---|
| Free Trial | 3 (lifetime, not monthly) | 10 | Yes |
| Starter | Configurable | Configurable | No |
| Pro | Configurable | Configurable | No |

- Free Trial is auto-assigned on first `GET /subscriptions/me/`
- Paid plans activated via Apple/Google In-App Purchase
- Usage resets monthly for paid plans; trial videos are a lifetime limit

---

## Management Commands

```bash
# Sync avatars from HeyGen API (run periodically to keep DB fresh)
docker compose exec web python manage.py sync_avatars

# Clear all avatars and re-sync
docker compose exec web python manage.py sync_avatars --clear

# Seed industries + backgrounds
docker compose exec web python manage.py seed_options

# Seed subscription plans
docker compose exec web python manage.py seed_plans
```

---

## Deployment Notes

> ⚠️ The following changes are required before going to production:

1. **Switch to PostgreSQL** — SQLite is not suitable for multi-worker production deployments
2. **Use Gunicorn** — Replace `runserver` with `gunicorn core.wsgi:application` in `docker-compose.yml` (already the Dockerfile default)
3. **Set `DEBUG=False`** and configure `ALLOWED_HOSTS` with your real domain
4. **Generate a strong `SECRET_KEY`** — never use the dev key in production
5. **Configure Apple/Google product IDs** in Django admin under Subscription Plans after deploying
6. **Run migrations on deploy:**
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py seed_options
   docker compose exec web python manage.py seed_plans
   docker compose exec web python manage.py sync_avatars
   ```

---

## License

MIT
