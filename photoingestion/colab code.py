# --- STEP 1: INSTALL (Standard Version) ---
!pip install git+https://github.com/huggingface/transformers accelerate qwen-vl-utils flask flask-ngrok pyngrok torch

# --- STEP 2: AUTHENTICATE NGROK ---
from pyngrok import ngrok
# REPLACE THIS WITH YOUR ACTUAL TOKEN
ngrok.set_auth_token("39fRisNQ0XmI09qGC3UDfdcv7cS_39oBAmbg3fBDb8EdYDFFx") 

# --- STEP 3: LOAD THE 2B MODEL (Stable) ---
import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

print("Loading Qwen2-VL-2B-Instruct (The Reliable One)...")

model = Qwen2VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen2-VL-2B-Instruct",
    torch_dtype=torch.float16,
    device_map="auto"
)
processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
print("BRAIN LOADED: Ready!")

# --- STEP 4: START SERVER ---
from flask import Flask, request, jsonify
from qwen_vl_utils import process_vision_info
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
public_url = ngrok.connect(5000).public_url

print(f"\n=== YOUR BRAIN IS LIVE AT: {public_url} ===\n")

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        image_url = data.get('image_url')
        prompt = data.get('prompt', "Describe this image.")

        # Minimal cleanup
        torch.cuda.empty_cache()

        messages = [
            {"role": "user", "content": [
                {"type": "image", "image": image_url},
                {"type": "text", "text": prompt},
            ]}
        ]

        text_input = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        
        inputs = processor(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to("cuda")

        # 2B is fast, so we can allow more tokens
        generated_ids = model.generate(**inputs, max_new_tokens=512)
        generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
        output_text = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

        return jsonify({"description": output_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

app.run(port=5000)