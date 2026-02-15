import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class HeyGenClient:
    """
    Client for interacting with the HeyGen API.
    Documentation: https://docs.heygen.com/reference
    """
    
    BASE_URL = "https://api.heygen.com"
    
    def __init__(self):
        self.api_key = getattr(settings, 'HEYGEN_API_KEY', None)
        if not self.api_key:
            logger.warning("HEYGEN_API_KEY is not set in settings.")
        
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

    def generate_video_agent(self, prompt, avatar_id=None):
        """
        Generates a video using the Video Agent (Prompt-to-Video) API.
        
        Args:
            prompt (str): The full prompt describing the video.
            avatar_id (str, optional): Specific Avatar ID to use.
            
        Returns:
            dict: The API response containing the video_id.
        """
        url = f"{self.BASE_URL}/v1/video_agent/generate"
        
        payload = {
            "prompt": prompt
        }
        
        if avatar_id:
            payload["config"] = {
                "avatar_id": avatar_id,
                "orientation": "portrait"  # Defaulting to portrait as per user snippet, or we could make it configurable
            }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()  # Expected: {"data": {"video_id": "..."}}
        except requests.exceptions.RequestException as e:
            logger.error(f"HeyGen API Generation Failed: {e}")
            if e.response:
                logger.error(f"Response: {e.response.text}")
            raise

    def check_status(self, video_id):
        """
        Checks the status of a video generation task.
        
        Args:
            video_id (str): The ID of the video to check.
            
        Returns:
            dict: The status response.
        """
        url = f"{self.BASE_URL}/v1/video_status.get"
        params = {"video_id": video_id}
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"HeyGen Status Check Failed: {e}")
            raise

    def get_avatars(self):
        """
        Fetches the list of avatars from HeyGen API with caching.
        Cache duration: 1 hour (3600 seconds)
        """
        from django.core.cache import cache
        
        CACHE_KEY = "heygen_avatars_list_v2"
        cached_data = cache.get(CACHE_KEY)
        
        if cached_data:
            return cached_data
            
        url = f"{self.BASE_URL}/v2/avatars"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            avatars = response.json().get('data', {}).get('avatars', [])
            
            # Cache the result if successful
            if avatars:
                cache.set(CACHE_KEY, avatars, timeout=3600)  # 1 Hour
                
            return avatars
        except requests.exceptions.RequestException as e:
            logger.error(f"HeyGen Avatar Fetch Failed: {e}")
            return []
    def get_avatar_details(self, avatar_id):
        """
        Fetches details for a specific avatar using the dedicated endpoint.
        """
        url = f"{self.BASE_URL}/v2/avatar/{avatar_id}/details"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json().get('data')
        except requests.exceptions.RequestException as e:
            logger.error(f"HeyGen Avatar Details Fetch Failed for {avatar_id}: {e}")
            # Fallback to list lookup if direct fetch fails? 
            # For now, let's return None so the view handles it (or falls back to defaults)
            return None
