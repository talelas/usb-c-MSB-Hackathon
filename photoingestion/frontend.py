import requests
import base64
import os
import mimetypes
from PIL import Image
import io

# --- CONFIGURATION ---
# PASTE YOUR NEW NGROK URL HERE EVERY TIME YOU RESTART COLAB
COLAB_URL = "https://longitudinal-rebiddable-naoma.ngrok-free.dev/analyze" 

def encode_image(image_path):
    """
    Resizes the image if it's too big, then converts to Base64.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Cannot find image: {image_path}")
        
    # Open the image using Pillow
    with Image.open(image_path) as img:
        # --- SAFETY RESIZE ---
        # If width or height is > 1024, shrink it.
        # This turns a 4MB phone pic into a lightweight KB file.
        max_size = 1024
        if img.width > max_size or img.height > max_size:
            print(f"Resizing image from {img.size} to safe size...")
            img.thumbnail((max_size, max_size))
            
        # Convert to RGB (fixes issues with transparent PNGs)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Save to memory buffer as JPEG (efficient compression)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        image_bytes = buffer.getvalue()

    # Encode the resized bytes
    encoded_string = base64.b64encode(image_bytes).decode('utf-8')
    
    # Always send as JPEG data URI since we converted it above
    return f"data:image/jpeg;base64,{encoded_string}"

def analyze_local_image(image_path, prompt="Describe this image detailedly."):
    """
    Sends a local image to the AI Brain.
    """
    print(f"Sending {image_path} to AI Brain...")
    
    try:
        # 1. Convert Image to Text String
        image_data = encode_image(image_path)
        
        # 2. Send to Colab
        response = requests.post(COLAB_URL, json={
            "image_url": image_data, 
            "prompt": prompt
        }, headers={"ngrok-skip-browser-warning": "true"})

        # 3. Handle Result
        if response.status_code == 200:
            return response.json().get('description', "No description returned.")
        else:
            print(f"Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"Connection Failed: {e}")
        return None

# --- TEST AREA ---
if __name__ == "__main__":
    # Ensure you have a file named 'test4.jpg' in the same folder as this script
    image_name = "test3.jpg" 
    
    if os.path.exists(image_name):
        result = analyze_local_image(image_name, "describe the image in detail .")
        print("\n--- AI SAYS ---\n")
        print(result)
    else:
        print(f"❌ Error: Please put an image named '{image_name}' in this folder to test.")