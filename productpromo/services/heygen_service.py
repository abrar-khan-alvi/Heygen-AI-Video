import logging
import requests
from django.conf import settings

# ── Shared HTTP utilities (no business logic, safe to import) ─────────────────
from videogen.services.heygen_service import (
    get_video_status,   # noqa: F401  re-exported for convenience
    get_video_status_standard, # noqa: F401
    get_session_status, # noqa: F401
    download_video,     # noqa: F401
    text_to_speech,     # noqa: F401
)

logger = logging.getLogger(__name__)

HEYGEN_BASE_URL = "https://api.heygen.com"
HEYGEN_UPLOAD_URL = "https://upload.heygen.com"


def _headers(content_type="application/json"):
    return {
        "X-Api-Key": settings.HEYGEN_API_KEY,
        "Content-Type": content_type,
        "Accept": "application/json",
    }


def upload_asset_to_heygen(file_path: str) -> str:
    """
    Upload a local image/video to HeyGen and return the asset_id.
    HeyGen v1 asset API requires raw binary data and specific Content-Type.
    """
    import mimetypes
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "image/jpeg"

    url = f"{HEYGEN_UPLOAD_URL}/v1/asset"
    logger.info(f"Uploading asset to HeyGen: {file_path} ({mime_type})")

    try:
        with open(file_path, "rb") as f:
            data = f.read()

        resp = requests.post(url, headers=_headers(mime_type), data=data, timeout=60)
        resp.raise_for_status()
        res_json = resp.json()
        res_data = res_json.get("data", {})
        asset_id = res_data.get("asset_id") or res_data.get("id")

        if not asset_id:
            raise Exception(f"No asset_id or id in upload response: {res_json}")

        logger.info(f"Asset uploaded successfully. ID: {asset_id}")
        return asset_id
    except Exception as e:
        logger.error(f"HeyGen asset upload failed: {e}")
        raise Exception(f"Failed to upload product image to HeyGen: {e}")


def _build_product_video_prompt(
    script: str,
    product_name: str,
    product_description: str,
    avatar_gender: str,
    background: str = "",
    has_asset: bool = False,
) -> str:
    """
    Constructs the HeyGen Video Agent prompt for a PRODUCT advertisement.

    Combines:
    - A chosen background / scene setting (or premium showroom fallback).
    - Explicit high-motion avatar performance instructions (natural hand gestures,
      body movement, leaning in, warm expression) — mirroring the videogen prompt.
    - Mandatory product asset (B-roll) usage when an asset is provided.
    """
    gender_desc = avatar_gender or "professional"
    background_location = background or (
        "modern high-end product showroom with soft studio lighting "
        "and subtle bokeh depth-of-field"
    )

    # ── Product asset instruction ──────────────────────────────────────────────
    asset_section = ""
    if has_asset:
        asset_section = (
            "\n\n=== CRITICAL: PRODUCT ASSET ===\n"
            "You MUST use 'Asset 1' for every single product-related visual. "
            "Asset 1 is the EXACT physical product — DO NOT use generic stock footage. "
            "Show 'Asset 1' in high-resolution close-ups whenever features are mentioned. "
            "Keep all product visuals strictly to 'Asset 1'."
        )

    # ── Background is the FIRST directive so HeyGen cannot ignore it ───────────
    prompt = f"""=== CRITICAL: BACKGROUND ENVIRONMENT (MANDATORY) ===
The avatar MUST appear inside a fully rendered, photorealistic real-world environment.
Background: {background_location}
NEVER use a black, blank, plain, dark, transparent, or empty background — this is a strict failure condition.
The environment must fill the entire frame with rich detail, cinematic depth-of-field,
professional lighting, and realistic textures. Render it as a premium advertisement set.
{asset_section}

=== CRITICAL: EYE CONTACT (MANDATORY) ===
The spokesperson MUST maintain direct, sustained eye contact with the camera lens at ALL times.
ALWAYS look straight into the camera — never look away, to the side, downward, or off-screen.
The avatar's gaze is locked to the viewer throughout the ENTIRE video, including while gesturing.
Looking away from the camera even briefly is a strict failure condition.
This is a direct-address advertisement: the spokesperson is always speaking TO the viewer.

=== AVATAR PERFORMANCE ===
Spokesperson: A highly dynamic and expressive {gender_desc} professional.
The avatar MUST deliver the script with exceptionally high energy and frequent, natural hand gestures.
Body movement: fluid weight shifts, leaning toward the camera for emphasis, periodic nodding.
Facial expression: warm smiles, genuine enthusiasm, unwavering direct eye contact with the camera lens.
Hands must be visible and actively gesturing in sync with the script's rhythm.
The goal is maximum realism and physical engagement — no static or robotic stillness.

=== PRODUCT ADVERTISEMENT ===
- Product: {product_name}
- Description: {product_description}
- Script (speak exactly): "{script}"

=== PRODUCTION STYLE ===
Create a high-quality 4K vertical (9:16) marketing video with cinematic lighting.
Warm accent lights that make both the spokesperson and the product pop.
Include a dynamic motion-graphics intro displaying the product name '{product_name}'.
Alternate between spokesperson A-roll (always looking directly into the camera) and product hero shots (B-roll).
Add bold social-media-style captions and upbeat background music.
End with a professional outro card featuring the product name.

FINAL REMINDER: The spokesperson MUST look directly into the camera lens at all times — never away.
The final video must be 30 seconds, 9:16 vertical, and feel like a premium human-led advertisement."""

    return prompt


def generate_video_standard(
    avatar_id: str,
    voice_id: str,
    script: str,
    product_name: str,
    product_description: str,
    avatar_gender: str = "professional",
    background: str = "",
    style_id: str = None,
    product_image_path: str = None,
) -> dict:
    """
    Submit a product promotional video job to HeyGen Video Agent.
    """
    # 1. Handle product image asset upload if provided
    asset_id = None
    if product_image_path:
        try:
            asset_id = upload_asset_to_heygen(product_image_path)
        except Exception as e:
            logger.warning(f"Failed to upload asset, proceeding without it: {e}")

    # 2. Build prompt (now includes background + high-motion instructions)
    url    = f"{HEYGEN_BASE_URL}/v1/video_agent/generate"
    prompt = _build_product_video_prompt(
        script=script,
        product_name=product_name,
        product_description=product_description,
        avatar_gender=avatar_gender,
        background=background,
        has_asset=bool(asset_id),
    )

    config: dict = {
        "avatar_id":    avatar_id,
        "duration_sec": 30,
        "orientation":  "portrait",
    }
    if voice_id:
        config["voice_id"] = voice_id

    payload = {"prompt": prompt, "config": config}

    # Pass the asset to Video Agent if available (root level per HeyGen docs)
    if asset_id:
        payload["files"] = [{"asset_id": asset_id}]

    logger.info(
        f"HeyGen Product Video — avatar: {avatar_id}, product: {product_name}, "
        f"background: '{background or 'default showroom'}'"
    )
    logger.info(f"HeyGen Product Video Prompt:\n{prompt}")

    try:
        resp = requests.post(url, headers=_headers(), json=payload, timeout=60)
        resp.raise_for_status()
        data     = resp.json()
        video_id = data.get("data", {}).get("video_id")
        if not video_id:
            raise Exception(f"No video_id in HeyGen response: {data}")
        logger.info(f"HeyGen product video started — video_id: {video_id}")
        return {"video_id": video_id}
    except requests.RequestException as e:
        body = ""
        if hasattr(e, "response") and e.response is not None:
            body = e.response.text
        logger.error(f"HeyGen product video error: {e} | {body}")
        raise Exception(f"Failed to generate product video: {e}")