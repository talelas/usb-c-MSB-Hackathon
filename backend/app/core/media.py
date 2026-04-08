"""Image captioning (Qwen2-VL) and audio transcription (faster-whisper).

All models are loaded inline and lazily initialized for process lifetime.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.config import (
    GENERATE_MEDIA_TEXT,
    VLM_PROMPT,
    WHISPER_MODEL,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
)

log = logging.getLogger(__name__)

# ── Image captioning (Qwen2-VL) ──────────────────────────────

_vlm_model = None
_vlm_processor = None


def _load_vlm():
    """Load Qwen2-VL model and processor (lazy init)."""
    global _vlm_model, _vlm_processor
    if _vlm_model is not None:
        return _vlm_model, _vlm_processor
    
    try:
        import torch
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
        from qwen_vl_utils import process_vision_info
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        log.info(f"Loading Qwen2-VL-2B-Instruct on {device}...")
        
        _vlm_model = Qwen2VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2-VL-2B-Instruct",
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto"
        )
        _vlm_processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
        log.info("✅ Qwen2-VL loaded successfully")
        return _vlm_model, _vlm_processor
    except Exception as exc:
        log.error(f"Failed to load Qwen2-VL: {exc}")
        return None, None


def get_caption(path: Path) -> str:
    """Generate image caption using Qwen2-VL."""
    if not GENERATE_MEDIA_TEXT:
        return ""
    
    try:
        import torch
        from qwen_vl_utils import process_vision_info
        
        model, processor = _load_vlm()
        if model is None or processor is None:
            return ""
        
        # Prepare message format for Qwen2-VL
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(path)},
                    {"type": "text", "text": VLM_PROMPT},
                ],
            }
        ]
        
        # Process inputs
        text_input = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        inputs = processor(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(device)
        
        # Generate caption
        generated_ids = model.generate(**inputs, max_new_tokens=512)
        
        # Decode output
        generated_ids_trimmed = [
            out_ids[len(in_ids):] 
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            generated_ids_trimmed, 
            skip_special_tokens=True, 
            clean_up_tokenization_spaces=False
        )[0]
        
        return output_text.strip()
        
    except torch.cuda.OutOfMemoryError as exc:
        log.warning(f"⚠️ CUDA OOM during caption for {path.name} - clearing cache and continuing without caption")
        try:
            torch.cuda.empty_cache()
        except:
            pass
        return ""
    except Exception as exc:
        log.warning(f"⚠️ Caption failed for {path.name}: {exc}")
        return ""


# ── Audio transcription ──────────────────────────────────────

_whisper_model = None


def transcribe_audio(path: Path) -> str:
    """Return an audio transcript (or empty string when generation is off)."""
    if not GENERATE_MEDIA_TEXT:
        return ""

    global _whisper_model
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("[media] faster-whisper not installed – skipping transcription")
        return ""

    if _whisper_model is None:
        _whisper_model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )

    try:
        segments, _ = _whisper_model.transcribe(str(path))
        parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        return " ".join(parts)
    except Exception as exc:
        print(f"[media] Transcription failed for {path.name}: {exc}")
        return ""
