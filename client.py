import requests
import base64
import os
import sys

# URL of your local server
SERVER_URL = "http://127.0.0.1:5000/analyze"

def encode_image(image_path):
    """Encodes a local image file to base64."""
    if not os.path.exists(image_path):
        print(f"❌ Error: File not found - {image_path}")
        sys.exit(1)
        
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:image/jpeg;base64,{encoded_string}"

if __name__ == "__main__":
    # Usage: python client.py my_image.jpg
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_image>")
        sys.exit(1)

    image_path = sys.argv[1]
    prompt = "Describe this image in detail."

    print(f"Sending {image_path} to local AI...")
    
    try:
        # 1. Encode Image
        image_b64 = encode_image(image_path)
        
        # 2. Send Request
        response = requests.post(SERVER_URL, json={
            "image_b64": image_b64,
            "prompt": prompt
        })

        # 3. Print Result
        if response.status_code == 200:
            print("\n--- 🤖 AI RESPONSE ---")
            print(response.json()['description'])
            print("----------------------\n")
        else:
            print(f"❌ Server Error: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is 'server.py' running?")