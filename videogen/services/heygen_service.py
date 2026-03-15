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
    outfit_instruction = f"- The spokesperson should appear in {outfit_desc} attire"

    background_instruction = ""
    if background:
        background_instruction = f"- CRITICAL VISUAL REQUIREMENT: When the avatar appears on screen, place them in front of a {background} background. This background should be consistent every time the avatar is shown. The background must ALWAYS be visible when the avatar is speaking. Do not use black, blank, transparent, or empty backgrounds."

    prompt = f"""Create a 30-second professional marketing video.

=== VIDEO TITLE ===
{title}

=== SPOKESPERSON ===
- Gender: {avatar_gender}
- Use a natural, professional {avatar_gender} voice that matches the avatar
{outfit_instruction}{background_instruction}

=== SCRIPT (spokesperson speaks these exact words) ===
{script}

=== VIDEO STYLE & PRODUCTION ===
Use clean, modern, professional styled visuals. Leverage motion graphics as B-rolls and A-roll overlays. Use AI-generated videos and images when helpful. When real-world footage is needed, use Stock Media. Include an intro sequence and outro sequence using Motion Graphics.

Specific visual directions:
- Opening: Start with a dynamic motion graphics intro (animated text/logo reveal with the title "{title}") before the avatar appears
- A-roll: Avatar speaking to camera with animated text overlays highlighting key points
- B-roll: Use relevant stock footage and motion graphics between avatar scenes to illustrate the {industry} service
- Motion graphics overlays: Display key benefits/features as animated text appearing while avatar speaks
- Transitions: Use smooth, professional transitions between scenes (not hard cuts)
- Lower thirds: Add subtle animated lower-third graphics
- Closing: End with a motion graphics outro card with call-to-action text overlay

=== FORMAT & PLATFORM ===
- Duration: 30 seconds
- Aspect ratio: 9:16 (vertical, optimized for TikTok, Instagram Reels, YouTube Shorts)
- Add auto-generated captions/subtitles (large, bold, centered — social media style)
- Pacing: Fast, punchy edits — keep viewer attention throughout
- Music: Add subtle, upbeat background music that matches the energy

=== COLOR & BRANDING ===
- Use a professional color palette suitable for {industry}
- Consistent typography and styling across all motion graphics
- Clean, minimal aesthetic — not cluttered

Make this video scroll-stopping, engaging, and ready to upload directly to social media."""

    return prompt


def generate_video(avatar_id, voice_id, script, title, industry, service_description,
                   avatar_gender, avatar_outfit, background=""):
    url = f"{HEYGEN_BASE_URL}/v1/video_agent/generate"

    prompt = _build_video_agent_prompt(
        script=script, title=title, industry=industry,
        service_description=service_description, avatar_gender=avatar_gender,
        avatar_outfit=avatar_outfit, background=background,
    )

    config_dict = {
        "avatar_id": avatar_id,
        "duration_sec": 33,
        "orientation": "portrait",
    }

    payload = {
        "prompt": prompt,
        "config": config_dict,
    }

    logger.info(f"HeyGen Video Agent — avatar: {avatar_id}, outfit: {avatar_outfit}")
    logger.info(f"HeyGen Video Agent Prompt: {prompt}")

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


def text_to_speech(voice_id, text, speed="1", language=None, locale=None):
    """
    Convert text to speech using a specific HeyGen voice.
    Returns the audio URL for playback.
    """
    url = f"{HEYGEN_BASE_URL}/v1/audio/text_to_speech"
    payload = {
        "text": text,
        "voice_id": voice_id,
        "input_type": "text",
        "speed": speed,
    }
    if language:
        payload["language"] = language
    if locale:
        payload["locale"] = locale

    try:
        resp = requests.post(url, headers=_headers(), json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        audio_url = data.get("data", {}).get("audio_url") or data.get("data", {}).get("url")
        if not audio_url:
            raise Exception(f"No audio URL in TTS response: {data}")
        logger.info(f"TTS generated for voice {voice_id}: {audio_url}")
        return {"audio_url": audio_url}
    except requests.RequestException as e:
        logger.error(f"HeyGen TTS error: {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"HeyGen TTS response: {e.response.text}")
        raise Exception(f"Text-to-speech failed: {e}")


def fetch_voices():
    """Fetch all available voices from HeyGen /v2/voices."""
    url = f"{HEYGEN_BASE_URL}/v2/voices"
    try:
        resp = requests.get(url, headers=_headers(), timeout=30)
        resp.raise_for_status()
        voices = resp.json().get("data", {}).get("voices", [])
        logger.info(f"HeyGen voices fetched: {len(voices)} voices")
        return voices
    except requests.RequestException as e:
        logger.error(f"HeyGen fetch voices error: {e}")
        raise Exception(f"Failed to fetch voices: {e}")


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