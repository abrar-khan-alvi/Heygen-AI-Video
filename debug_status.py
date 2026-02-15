import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from videos.heygen_service import HeyGenClient

def check_status():
    video_id = "8cd86ad7fedb42508a8a27b059379603"
    client = HeyGenClient()
    try:
        print(f"Checking status for {video_id}...")
        response = client.check_status(video_id)
        print("Raw Response:", response)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_status()
