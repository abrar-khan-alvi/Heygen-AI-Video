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
    
    # Absolute barebones prompt format proven to work
    prompt = (
        f"Create a high-quality vertical promotional video for the {industry} industry. "
        f"Video Title: {title}. "
        f"Service Description: {service_description}. "
        f"The Avatar is a {avatar_gender} dressed in {outfit_desc} attire. "
        f"CRITICAL VISUAL REQUIREMENT: Whenever the avatar appears in the frame, the background behind them MUST be a realistic {bg_desc}. "
        f"The background must ALWAYS be visible when the avatar is speaking. Do not use black, blank, transparent, or empty backgrounds. "
        f"Please speak the following exact script naturally and professionally:\n\n"
        f"\"{script}\"\n\n"
        f"Make it highly engaging, professional, and optimized for social media."
    )
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
    
    # HeyGen's /v1/video_agent/generate endpoint strictly rejects 'voice_id' in config:
    # "config.voice_id is invalid: Extra inputs are not permitted"
    # The avatar's default voice will be used instead.

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