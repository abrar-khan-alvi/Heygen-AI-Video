import os
import django
import requests
import json
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def fetch_and_save_avatars():
    api_key = settings.HEYGEN_API_KEY
    url = "https://api.heygen.com/v2/avatars"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        print("Fetching avatars from HeyGen...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        avatars = response.json().get('data', {}).get('avatars', [])
        
        print(f"Found {len(avatars)} total avatars.")
        
        processed_avatars = []
        
        keywords = {
            "Business": ["suit", "office", "formal", "shirt", "business", "professional", "news"],
            "Casual": ["casual", "public", "t-shirt", "hoodie", "sweater", "sofa", "street", "outdoor"],
            "Doctor": ["doctor", "coat", "medical", "nurse"],
            "Sport": ["sport", "gym", "fitness", "yoga", "active"]
        }

        for avatar in avatars:
            # Basic validation
            if not avatar.get('preview_image_url'):
                continue
                
            name = avatar.get('name', 'Unknown')
            avatar_id = avatar.get('avatar_id')
            gender = avatar.get('gender', 'unknown')
            
            # Auto-tagging Outfit
            outfit = "Casual" # Default
            name_lower = name.lower()
            id_lower = avatar_id.lower()
            
            for category, tags in keywords.items():
                if any(tag in name_lower or tag in id_lower for tag in tags):
                    outfit = category
                    break
            
            # Auto-tagging Pose
            pose = "Standing" # Default
            if "sitting" in id_lower or "sofa" in id_lower or "chair" in id_lower:
                pose = "Sitting"
            elif "closeup" in id_lower or "portrait" in id_lower or "head" in id_lower:
                pose = "Closeup"
            
            processed_avatars.append({
                "id": avatar_id,
                "name": name,
                "gender": gender.capitalize(), 
                "outfit": outfit,
                "pose": pose,
                "preview_url": avatar.get('preview_image_url')
            })
            
        # Save to file in the videos app directory
        output_path = os.path.join(settings.BASE_DIR, 'videos', 'avatars.json')
        with open(output_path, 'w') as f:
            json.dump(processed_avatars, f, indent=2)
            
        print(f"Saved {len(processed_avatars)} avatars to {output_path}")
        
        # Print some stats
        print("\nBreakdown by Outfit:")
        for key in keywords.keys():
            count = len([a for a in processed_avatars if a['outfit'] == key])
            print(f"  {key}: {count}")

        print("\nBreakdown by Pose:")
        for key in ["Standing", "Sitting", "Closeup"]:
            count = len([a for a in processed_avatars if a['pose'] == key])
            print(f"  {key}: {count}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_and_save_avatars()
