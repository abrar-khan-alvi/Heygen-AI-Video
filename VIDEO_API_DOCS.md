# HeyGen Video API Documentation

## Overview
Generate AI marketing videos using HeyGen's Video Agent.

## Endpoints

### 1. Generate Video Script (Gemini)
**POST** `/api/v1/videos/generate-script/`

Generates a marketing script based on a topic using Google Gemini AI.

**Body:**
```json
{
  "title": "Luxury Watch Marketing",
  "industry": "Fashion",
  "service_description": "Swiss-made automatic watches",
  "gender": "Male",
  "outfit": "Tuxedo",
  "background": "Luxury Penthouse",
  "duration": "30 seconds"
}
```

**Response:** `200 OK`
```json
{
  "script": "**Hook:** (0:00-0:05)\n[Close up of watch face...]\n"
}
```

### 2. Generate Video
**POST** `/api/v1/videos/projects/`

Creates a new project and starts the generation process in the background.

**Body:**
```json
{
  "industry": "Real Estate",
  "service_description": "Luxury condos in downtown with sea view",
  "gender": "Female",
  "background_type": "Modern Office",
  "avatar_outfit": "Business Suit"
}
```

**Response:** `201 Created`
```json
{
  "id": "a1b2c3d4-e5f6-...",
  "status": "PROCESSING",
  "heygen_video_id": "v1234567890",
  "constructed_prompt": "Create a high-quality marketing video for the Real Estate industry...",
  "created_at": "2026-02-14T21:06:30.291620Z"
}
```

### 3. List Available Avatars
**Endpoint:** `GET /api/v1/videos/avatars/`

**Query Parameters:**
- `gender` (optional): `Male` or `Female`
- `outfit` (optional): `Business`, `Casual`, `Doctor`, `Sport`
- `pose` (optional): `Standing`, `Sitting`, `Closeup`

**Response:**
```json
[
    {
        "id": "Abigail_expressive_2024112501",
        "name": "Abigail",
        "gender": "Female",
        "outfit": "Casual",
        "pose": "Standing",
        "preview_url": "..."
    }
]
```

### 5. Check Real-Time Video Status
**Endpoint:** `GET /api/v1/videos/projects/{id}/status/`
This forces a check against HeyGen's API and updates the local database.

**Response:**
```json
{
    "id": "b2cdda19-4dbb-4de0-98cf-642252df55cc",
    "heygen_video_id": "8cd86ad7fedb42508a8a27b059379603",
    "status": "COMPLETED",
    "heygen_status": "completed",
    "video_url": "https://heygen.com/video/...",
    "error": null
}
```

### 2. Check Status / Get Video
**GET** `/api/v1/videos/projects/{id}/`

Poll this endpoint to check if the video is ready.

**Response:** `200 OK`
```json
{
  "id": "uuid-string",
  "status": "COMPLETED",  // or PENDING, PROCESSING, FAILED
  "video_url": "https://heygen.com/video/...",  // Null if not ready
  "constructed_prompt": "..."
}
```

### 3. List My Videos
**GET** `/api/v1/videos/projects/`

Returns a list of all videos created by the user.
