"""
Gemini AI script generation using the new Google GenAI SDK (google-genai).
All videos are fixed at ~30 seconds.
Scripts contain ONLY the words the spokesperson will speak on camera.
"""

import logging
from google import genai
from django.conf import settings

logger = logging.getLogger(__name__)

VIDEO_DURATION_SECONDS = 30
WORD_COUNT = 75


def _get_client():
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_script(industry, service_description, avatar_gender, avatar_outfit,
                     title="", background=""):
    background_context = ""
    if background:
        background_context = f"\n- Setting/Background: {background}"

    prompt = f"""You are writing a script for a spokesperson in a 30-second social media marketing video.
The video will have B-roll footage, motion graphics, and animated overlays between the spoken parts.

Details:
- Video Title: {title}
- Industry: {industry}
- Service/Product: {service_description}
- Spokesperson: {avatar_gender}{background_context}

STRICT RULES:
1. Write EXACTLY 70-80 words total. Critical for 30-second timing.
2. Write ONLY the words the spokesperson speaks out loud. Nothing else.
3. Structure the script in 4 natural beats (don't label them, just write them as separate paragraphs):
   - Beat 1 (~15 words): A punchy hook that grabs attention in the first 3 seconds
   - Beat 2 (~25 words): The problem or pain point the audience faces
   - Beat 3 (~25 words): How the service solves it (key value proposition)
   - Beat 4 (~10 words): A clear, bold call-to-action
4. Do NOT include:
   - Stage directions, camera notes, scene descriptions
   - Character names or labels
   - Headings, bullet points, or formatting
   - Parenthetical notes of any kind
   - Beat numbers or labels
5. Use short, punchy sentences. This is for social media — not a corporate presentation.
6. Write in first person plural ("we") when referring to the company.
7. Make it conversational, energetic, and scroll-stopping.

Output ONLY the spoken script. Start directly with the first word."""

    try:
        client = _get_client()
        model_name = getattr(settings, "GEMINI_MODEL", "gemini-3-pro-preview")

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        script = response.text.strip()
        if not script:
            raise Exception("Gemini returned an empty response.")
        return script
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        raise Exception(f"Failed to generate script: {e}")