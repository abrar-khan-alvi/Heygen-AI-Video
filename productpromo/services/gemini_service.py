"""
productpromo/services/gemini_service.py

Completely independent from videogen/services/gemini_service.py.

Context: product promotional videos.
Inputs:  product_name, product_description, avatar_gender, image_path (optional).
Output:  70-80 word spoken script in 4 beats.

When image_path is supplied, Gemini receives the actual product image as an
inlineData part (multimodal) so it can reference visual details — colours,
packaging shape, texture, branding — in the script.
"""

import logging
import mimetypes
from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)

WORD_COUNT_TARGET = "70-80"
VIDEO_DURATION    = "30-second"


def _get_client():
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _build_prompt(product_name: str, product_description: str,
                  avatar_gender: str, has_image: bool) -> str:
    image_note = (
        "A product image is provided — analyse it carefully and weave the visual "
        "details (colours, packaging, texture, style, branding) into the script "
        "to make it vivid and product-specific."
        if has_image else
        "No image provided — work from the text description only."
    )

    return f"""You are writing a script for a spokesperson in a {VIDEO_DURATION} product promotional video for social media.

Product Details:
- Product Name: {product_name}
- Description: {product_description}
- Spokesperson: {avatar_gender or "professional"}
- Image guidance: {image_note}

STRICT RULES:
1. Write EXACTLY {WORD_COUNT_TARGET} words total. Critical for {VIDEO_DURATION} timing.
2. Write ONLY the words the spokesperson speaks out loud. Nothing else.
3. Structure in 4 natural beats (separate paragraphs, NO labels, NO headings):
   - Beat 1 (~15 words): Punchy hook that grabs attention in 3 seconds — specific to THIS product.
   - Beat 2 (~20 words): The problem or desire this product directly addresses.
   - Beat 3 (~30 words): Exactly how THIS product solves it — reference real features or appearance.
   - Beat 4 (~10 words): Clear, bold call-to-action.
4. Do NOT include: stage directions, camera notes, headings, bullet points, parenthetical notes,
   beat labels, or any text other than what the spokesperson speaks.
5. Short, punchy sentences — social media tone, not corporate.
6. Use "we" when referring to the brand/company.
7. Be creative with the hook — do NOT start with "Stop scrolling!" or "Attention!".
8. Reference specifics: if the product has a colour, shape, or unique feature — name it.

Output ONLY the spoken script. Start directly with the first word."""


def generate_product_script(product_name: str, product_description: str,
                             avatar_gender: str = "professional",
                             image_path: str = None) -> str:
    """
    Generate a product promotional video script via Gemini.

    Args:
        product_name:        Name of the product.
        product_description: Description, features, target audience.
        avatar_gender:       Gender of the spokesperson ("male" / "female" / "professional").
        image_path:          Absolute filesystem path to the uploaded product image.
                             If provided, uses Gemini multimodal (image + text).
                             If None, falls back to text-only generation.

    Returns:
        Script string (70-80 words).

    Raises:
        Exception on Gemini error.
    """
    client     = _get_client()
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    has_image  = bool(image_path)
    prompt_text = _build_prompt(product_name, product_description, avatar_gender, has_image)

    try:
        if has_image:
            # ── Multimodal: read image bytes from disk ──────────────────────
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type or not mime_type.startswith("image/"):
                mime_type = "image/jpeg"  # safe default

            with open(image_path, "rb") as f:
                image_bytes = f.read()

            contents = [
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                types.Part.from_text(text=prompt_text),
            ]
        else:
            # ── Text-only fallback ──────────────────────────────────────────
            contents = [types.Part.from_text(text=prompt_text)]

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
        )

        script = (response.text or "").strip()
        if not script:
            raise Exception("Gemini returned an empty response.")

        logger.info(
            f"Product script generated for '{product_name}' "
            f"({'multimodal' if has_image else 'text-only'}), "
            f"{len(script.split())} words."
        )
        return script

    except Exception as e:
        logger.error(f"Gemini product script error: {e}")
        raise Exception(f"Failed to generate product script: {e}")
