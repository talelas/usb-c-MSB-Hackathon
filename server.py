import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
from flask import Flask, request, jsonify
from PIL import Image
import io
import base64
import logging

# --- CONFIGURATION ---
# Use "cuda" for NVIDIA GPU, "cpu" for no GPU, or "mps" for Mac
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
PORT = 5000

# --- 1. LOAD MODEL ---
print(f"Loading Qwen2-VL-2B-Instruct on {DEVICE}...")

try:
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct",
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
        device_map="auto"
    )
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
    print("✅ Model Loaded Successfully!")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    exit(1)

# --- 2. SETUP SERVER ---
# Mute Flask logs to keep terminal clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

def decode_base64_image(image_string):
    """Converts base64 string back to a PIL Image."""
    if "base64," in image_string:
        image_string = image_string.split("base64,")[1]
    image_bytes = base64.b64decode(image_string)
    return Image.open(io.BytesIO(image_bytes))

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        image_b64 = data.get('image_b64') # Expects base64 string
        prompt = data.get('prompt', "Describe this image.")
        
        print(f"📩 Received Request: {prompt}")

        # Convert base64 to PIL Image
        image = decode_base64_image(image_b64)

        # Prepare messages
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        # Prepare inputs
        text_input = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        
        inputs = processor(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(DEVICE)

        # Generate
        generated_ids = model.generate(**inputs, max_new_tokens=512)
        
        # Decode
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]

        print(f"📤 Sending Response: {output_text[:50]}...")
        return jsonify({"description": output_text})

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print(f"🚀 Server running at http://127.0.0.1:{PORT}")
    app.run(host='0.0.0.0', port=PORT)