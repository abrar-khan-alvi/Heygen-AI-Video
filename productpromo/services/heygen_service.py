import logging
import requests
from django.conf import settings

# ── Shared HTTP utilities (no business logic, safe to import) ─────────────────
from videogen.services.heygen_service import (
    get_video_status,   # noqa: F401  re-exported for convenience
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
        data = res_json.get("data", {})
        asset_id = data.get("asset_id") or data.get("id")
        
        if not asset_id:
            raise Exception(f"No asset_id or id in upload response: {res_json}")
        
        logger.info(f"Asset uploaded successfully. ID: {asset_id}")
        return asset_id
    except Exception as e:
        logger.error(f"HeyGen asset upload failed: {e}")
        raise Exception(f"Failed to upload product image to HeyGen: {e}")


def _build_product_video_prompt(script: str, product_name: str,
                                 product_description: str, avatar_gender: str,
                                 has_asset: bool = False) -> str:
    """
    Constructs the HeyGen Video Agent prompt for a PRODUCT advertisement.
    Balanced for high avatar visibility and mandatory product asset usage.
    """
    gender_desc = avatar_gender or "professional"

    asset_instruction = ""
    if has_asset:
        asset_instruction = (
            "CRITICAL VISUAL REQUIREMENT: You MUST use 'Asset 1' for every single product-related visual. "
            "Asset 1 is the EXACT physical product (a high-tech E-bike). DO NOT use generic stock footage of regular bicycles or seats. "
            "When the script mentions features, show 'Asset 1' in high-resolution close-ups. Keep the visual context strictly to 'Asset 1'."
        )

    return f"""Create a photorealistic vertical promotional video for the product '{product_name}'.

{asset_instruction}

=== SPOKESPERSON (A-ROLL) ===
- Lead Actor: A {gender_desc} spokesperson (delivered via the configured Avatar ID).
- Performance: High energy, enthusiastic, and directly presenting the product to the camera.
- Visibility: The spokesperson should be the primary focus of the video. 

=== PRODUCT VISUALS (B-ROLL) ===
- Asset: Use 'Asset 1' for ALL product-specific scenes. 
- Presentation: Show 'Asset 1' as a side-overlay while the spokesperson talks, AND as a full-screen feature close-up during key descriptive moments.

=== SCRIPT ===
The spokesperson speaks this EXACT script:
"{script}"

=== VIDEO STRUCTURE ===
1. START: Spokesperson on screen immediately, welcoming the viewer. Display the product name '{product_name}' as a modern text overlay.
2. FEATURE SHOWCASE: As the spokesperson describes features, transition between full-screen spokesperson and full-screen hero shots of 'Asset 1'. 
3. CALL TO ACTION: End with the spokesperson and a final professional graphic showing the product name.

=== STYLE ===
- Layout: Vertical 9:16.
- Background: A high-end, photorealistic modern showroom or a bright urban lifestyle setting. DO NOT use a black or blank background. The environment must be professional and look like a premium advertisement.
- Lighting: Professional studio lighting with warm accents that make the product (Asset 1) and the spokesperson pop.
- Captions: Bold, legible dynamic social-media style captions.
- Music: Upbeat, trendy background music.
"""


def generate_product_video(avatar_id: str, voice_id: str, script: str,
                            product_name: str, product_description: str,
                            avatar_gender: str = "professional",
                            product_image_path: str = None) -> dict:
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

    # 2. Build prompt
    url    = f"{HEYGEN_BASE_URL}/v1/video_agent/generate"
    prompt = _build_product_video_prompt(
        script=script,
        product_name=product_name,
        product_description=product_description,
        avatar_gender=avatar_gender,
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
    
    # Pass the asset to Video Agent if available (at the root level per documentation)
    if asset_id:
        payload["files"] = [{"asset_id": asset_id}]

    logger.info(
        f"HeyGen Product Video — avatar: {avatar_id}, product: {product_name}"
    )

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
