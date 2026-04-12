import subprocess
import logging
import os
import tempfile
from django.conf import settings

logger = logging.getLogger(__name__)

def apply_watermark(input_video_content, output_filename):
    """
    Applies a watermark logo to the input video content using FFmpeg.
    Returns a ContentFile of the watermarked video.
    """
    from django.core.files.base import ContentFile

    logo_path = os.path.join(settings.MEDIA_ROOT, "logo.png")
    
    if not os.path.exists(logo_path):
        logger.error(f"Watermark logo not found at {logo_path}. Returning original video.")
        return ContentFile(input_video_content, name=output_filename)

    # Use temporary files for processing
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_input:
        temp_input.write(input_video_content)
        temp_input_path = temp_input.name

    temp_output_path = temp_input_path.replace(".mp4", "_watermarked.mp4")

    # FFmpeg command: 
    # 1. Use scale2ref to scale stream [1:v] (logo) relative to [0:v] (video)
    # 2. Set logo width to 15% of video width (iw*0.15)
    # 3. Position in bottom-right with 20px padding (overlay=W-w-20:H-h-20)
    command = [
        "ffmpeg", "-y",
        "-i", temp_input_path,
        "-i", logo_path,
        "-filter_complex", "[1:v][0:v]scale2ref=w=iw*0.15:h=-1[logo][video];[video][logo]overlay=W-w-20:H-h-20",
        "-codec:a", "copy",
        temp_output_path
    ]

    try:
        logger.info(f"Applying scaled watermark (15% width) to {output_filename}...")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info(f"Watermark applied successfully to {output_filename}")
        
        with open(temp_output_path, "rb") as f:
            watermarked_content = f.read()
            
        return ContentFile(watermarked_content, name=output_filename)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        # Fallback to original content on failure
        return ContentFile(input_video_content, name=output_filename)
    finally:
        # Cleanup
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
