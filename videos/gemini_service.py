import google.generativeai as genai
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class GeminiService:
    """
    Service to interact with Google's Gemini AI for script generation.
    """
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            logger.error("GEMINI_API_KEY is not set.")
            raise ValueError("GEMINI_API_KEY is not set in environment variables.")
            
        genai.configure(api_key=self.api_key)
        # Use gemini-1.5-flash as it is the current standard and faster/cheaper
        self.model = genai.GenerativeModel('gemini-3-flash-preview')

    def generate_script(self, title, industry, service_description, gender, outfit, background, duration="30 seconds"):
        """
        Generates a video script based on detailed project context.
        """
        try:
            prompt = (
                f"You are a professional video scriptwriter for HeyGen AI. Your goal is to generate a compelling video script for an avatar.\n\n"
                f"**Project Context:**\n"
                f"- Title: {title}\n"
                f"- Industry: {industry}\n"
                f"- Service/Product: {service_description}\n"
                f"- Target Audience: Potential clients/customers\n"
                f"- Visual Style: {background}\n"
                f"- Avatar Persona: {gender} in {outfit}\n"
                f"- Target Duration: {duration}\n\n"
                f"**Instructions:**\n"
                f"1. Generate the script tailored specifically for a {duration} video.\n"
                f"2. Structure the output as a JSON object with the following schema:\n"
                f"   {{\n"
                f"     \"script_text\": \"The exact spoken words for the avatar. Use natural punctuation.\"\n"
                f"   }}\n"
                f"3. Ensure the content is engaging, professional, and directly addresses the audience.\n"
                f"4. ONLY generate the spoken script. Do NOT include scene numbers, visual descriptions, or titles."
            )
            
            logger.info(f"Generating script for title: {title}")
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            if response.text:
                return response.text
            else:
                logger.error("Gemini returned empty response.")
                return None
                
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return None
