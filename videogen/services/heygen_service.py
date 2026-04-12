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
    background_location = background or "modern, high-end professional office with cinematic lighting"
    
    # Narratively described scene and performance
    scene_description = (
        f"A cinematic vertical video featuring a highly dynamic and expressive {avatar_gender} professional. "
        f"Location/Setting: The avatar is standing in a {background_location}. "
        f"The environment must be photorealistic, detailed, and visually engaging—avoid plain or blank backgrounds. "
        f"Behavior: The avatar must deliver the script with exceptionally high energy and frequent, natural hand gestures. "
        f"They should move their body fluidly, leaning in toward the camera for emphasis, nodding periodically, "
        f"and maintaining a constant sense of human-like presence through subtle shifts in posture and warm smiles. "
        f"The goal is maximum realism and physical engagement—avoiding any static or robotic stillness."
    )

    prompt = f"""{scene_description}

=== VIDEO CONTENT ===
- Industry: {industry}
- Title: {title}
- Outfit: {outfit_desc} attire
- Script (speak exactly): "{script}"

=== PRODUCTION STYLE ===
Create a high-quality 4k marketing video. Use cinematic lighting and depth-of-field.
Include a dynamic motion graphics intro with the title "{title}".
Interchange between the avatar speaking (A-roll) and relevant professional stock media/motion graphics (B-roll) that illustrates the {industry} service.
Add bold social-media style captions and upbeat background music.
End with a professional outro card.

=== AVATAR PERFORMANCE ===
The avatar should be the star of the show, exhibiting a 'high-motion' performance. 
Ensure the hands are visible and actively gesturing in sync with the script's rhythm. 
The body should shift and move naturally, creating a sense of three-dimensional space and high-end production realism.

The final video must be 30 seconds, 9:16 vertical, and feel like a premium, human-led advertisement."""

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
        "duration_sec": 30,
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

    if not text or not text.strip():
        raise Exception("Cannot generate TTS: text is empty. Please generate a script for the project first.")

    # HeyGen TTS Starfish v1 API: simplified payload first to verify fix
    # Speed is an optional string field if used.
    payload = {
        "text": text,
        "voice_id": voice_id,
    }
    if language:
        payload["language"] = language
    
    logger.info(f"HeyGen TTS payload — voice: {voice_id}, text_len: {len(text)}")

    try:
        resp = requests.post(url, headers=_headers(), json=payload, timeout=60)
        if not resp.ok:
            error_text = resp.text
            if "STARFISH" in error_text:
                friendly_error = (
                    "This voice is not compatible with HeyGen's preview engine (Starfish). "
                    "Please re-sync your voice library or select a different voice."
                )
                logger.error(f"HeyGen Starfish incompatibility: {error_text}")
                raise Exception(friendly_error)
                
            logger.error(f"HeyGen TTS error {resp.status_code}: {error_text}")
            raise Exception(f"HeyGen TTS error {resp.status_code}: {error_text}")
            
        resp.raise_for_status()
        data = resp.json()
        
        # Starfish v1 response shape check
        audio_url = data.get("data", {}).get("audio_url")
        if not audio_url:
            # Fallback checks
            audio_url = data.get("data", {}).get("url") or data.get("url")
            
        if not audio_url:
            raise Exception(f"No audio URL in TTS response: {data}")
            
        logger.info(f"TTS generated for voice {voice_id}: {audio_url}")
        return {"audio_url": audio_url}
    except requests.RequestException as e:
        error_body = ""
        if hasattr(e, "response") and e.response is not None:
            error_body = f" | Response: {e.response.text}"
        logger.error(f"HeyGen TTS request error: {e}{error_body}")
        raise Exception(f"Text-to-speech failed: {e}{error_body}")


def fetch_voices():
    """Fetch all available voices from HeyGen /v1/audio/voices."""
    url = f"{HEYGEN_BASE_URL}/v1/audio/voices"
    try:
        resp = requests.get(url, headers=_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        voices = data.get("data", [])
        if not isinstance(voices, list):
            voices = []
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