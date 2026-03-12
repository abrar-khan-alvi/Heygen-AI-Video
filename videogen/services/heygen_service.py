"""
HeyGen API service.

Endpoints used:
  - Video Agent:  POST /v1/video_agent/generate
  - Video Status: GET  /v1/video_status.get

Avatar listing is served from CachedAvatar DB table (synced via sync_avatars command).
"""

import logging
import requests
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

HEYGEN_BASE_URL = "https://api.heygen.com"


def _headers():
    return {
        "X-Api-Key": settings.HEYGEN_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _build_video_agent_prompt(script, title, industry, service_description,
                               avatar_gender, avatar_outfit, background):
    outfit_desc = avatar_outfit or "professional"
    bg_desc = background or "professional office"
    
    prompt = (
        f"Create a high-quality professional marketing video for the {industry} industry. "
        f"Video Title: {title}. "
        f"Service Description: {service_description}. "
        f"The presenter is a {avatar_gender} wearing {outfit_desc} attire. "
        
        # Explicitly command the agent to GENERATE the background image:
        f"Generate a highly detailed background image of a {bg_desc} and composite the presenter over it. Ensure the background is not black or empty. "
        
        f"Please speak the following exact script naturally and professionally:\n\n"
        f"\"{script}\"\n\n"
        f"Use clean, modern, professional styled visuals. Leverage motion graphics as A-roll overlays "
        f"and include relevant B-roll footage where appropriate. Include an intro and outro with "
        f"the title '{title}'. Add social-media style captions. "
        f"The video duration must be approximately 30 seconds."
    )
    return prompt


def generate_video(avatar_id, script, title, industry, service_description,
                   avatar_gender, avatar_outfit, background=""):
    url = f"{HEYGEN_BASE_URL}/v1/video_agent/generate"

    prompt = _build_video_agent_prompt(
        script=script, title=title, industry=industry,
        service_description=service_description, avatar_gender=avatar_gender,
        avatar_outfit=avatar_outfit, background=background,
    )

    payload = {
        "prompt": prompt,
        "config": {
            "avatar_id": avatar_id,
            "duration_sec": 30,
            "orientation": "portrait",
        },
    }

    logger.info(f"HeyGen Video Agent — avatar: {avatar_id}, outfit: {avatar_outfit}")

    try:
        resp = requests.post(url, headers=_headers(), json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        video_id = data.get("data", {}).get("video_id")
        if not video_id:
            raise Exception(f"No video_id in response: {data}")
        logger.info(f"HeyGen Video Agent started — video_id: {video_id}")
        return {"video_id": video_id}
    except requests.RequestException as e:
        logger.error(f"HeyGen Video Agent error: {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"HeyGen response: {e.response.text}")
        raise Exception(f"Failed to generate video: {e}")


def download_video(video_url, filename):
    try:
        resp = requests.get(video_url, timeout=120, stream=True)
        resp.raise_for_status()
        if not filename.endswith(".mp4"):
            filename = f"{filename}.mp4"
        return ContentFile(resp.content, name=filename)
    except requests.RequestException as e:
        logger.error(f"Download failed from {video_url}: {e}")
        raise Exception(f"Failed to download video: {e}")


def get_video_status(video_id):
    url = f"{HEYGEN_BASE_URL}/v1/video_status.get"
    try:
        resp = requests.get(url, headers=_headers(), params={"video_id": video_id}, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        heygen_status = data.get("status", "unknown")
        return {
            "status": heygen_status,
            "video_url": data.get("video_url") if heygen_status == "completed" else None,
            "message": data.get("error", "") or f"Video status: {heygen_status}",
        }
    except requests.RequestException as e:
        logger.error(f"HeyGen status error: {e}")
        raise Exception(f"Failed to get video status: {e}")