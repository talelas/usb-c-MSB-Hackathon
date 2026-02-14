import requests
import base64
import os
import sys
import io
from PIL import Image  # Requires: pip install Pillow

# --- CONFIGURATION ---
SERVER_URL = "http://127.0.0.1:5000/analyze"
IMAGE_FILENAME = "test4.jpg"  # <--- CHANGE THIS to your actual image file name

def encode_image(image_path):
    """
    Resizes the image if it's too big, then converts to Base64.
    """
    if not os.path.exists(image_path):
        print(f"❌ Error: File not found - {image_path}")
        print(f"   (Make sure '{image_path}' is in the same folder as this script)")
        sys.exit(1)
        
    try:
        # Open the image using Pillow
        with Image.open(image_path) as img:
            # --- SAFETY RESIZE ---
            # If width or height is > 1024, shrink it.
            max_size = 1024
            if img.width > max_size or img.height > max_size:
                print(f"⚠️ Image is large ({img.size}). Resizing to safe size...")
                img.thumbnail((max_size, max_size))
                
            # Convert to RGB (fixes issues with transparent PNGs)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Save to memory buffer as JPEG
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            image_bytes = buffer.getvalue()

        # Encode the resized bytes
        encoded_string = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded_string}"
        
    except Exception as e:
        print(f"❌ Error processing image: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # No command line arguments needed now.
    print(f"🚀 Loading '{IMAGE_FILENAME}'...")
    
    prompt = "Describe this image in detail."

    try:
        # 1. Encode Image (with resizing)
        image_b64 = encode_image(IMAGE_FILENAME)
        
        print(f"📤 Sending to {SERVER_URL}...")
        
        # 2. Send Request
        response = requests.post(SERVER_URL, json={
            "image_b64": image_b64,
            "prompt": prompt
        })

        # 3. Print Result
        if response.status_code == 200:
            print("\n--- 🤖 AI RESPONSE ---")
            print(response.json().get('description', 'No description received'))
            print("----------------------\n")
        else:
            print(f"❌ Server Error: {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server.")
        print(f"   Is 'server.py' running at {SERVER_URL}?")