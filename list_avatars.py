import os
import django
import requests
import json
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def list_avatars():
    api_key = settings.HEYGEN_API_KEY
    url = "https://api.heygen.com/v2/avatars"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        avatars = response.json().get('data', {}).get('avatars', [])
        
        keywords = {
            "Business": ["suit", "office", "formal", "shirt", "business"],
            "Casual": ["casual", "public", "t-shirt", "hoodie", "sweater", "sofa"],
            "Doctor": ["doctor", "coat", "medical"],
            "Sport": ["sport", "gym", "fitness", "yoga"]
        }
        
        found = {k: [] for k in keywords}
        
        for avatar in avatars:
            name_lower = avatar.get('name', '').lower()
            id_lower = avatar.get('avatar_id', '').lower()
            
            for category, tags in keywords.items():
                if any(tag in name_lower or tag in id_lower for tag in tags):
                    expected_gender = 'male' if 'male' == avatar.get('gender') else 'female'
                    found[category].append({
                        "id": avatar.get('avatar_id'),
                        "name": avatar.get('name'),
                        "gender": avatar.get('gender'),
                        "preview": avatar.get('preview_image_url')
                    })

        with open('avatars_by_outfit.txt', 'w') as f:
            for category, items in found.items():
                f.write(f"\n=== {category} ({len(items)}) ===\n")
                # Separate by gender for better visibility
                males = [x for x in items if x['gender'] == 'male']
                females = [x for x in items if x['gender'] == 'female']
                
                f.write(f"  -- Males ({len(males)}) --\n")
                for item in males[:5]:
                    f.write(f"  {item['name']} (ID: {item['id']})\n")
                    f.write(f"  Img: {item['preview']}\n")
                    
                f.write(f"  -- Females ({len(females)}) --\n")
                for item in females[:5]:
                    f.write(f"  {item['name']} (ID: {item['id']})\n")
                    f.write(f"  Img: {item['preview']}\n")
                    
        print("Categorized avatars written to avatars_by_outfit.txt")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_avatars()
