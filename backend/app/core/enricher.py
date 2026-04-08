"""Ollama-based semantic enrichment (summary + keywords).

Kept separate from the LLM chat module because enrichment uses
a specific, constrained prompt style and short timeouts.
"""
from __future__ import annotations

from typing import List

import requests

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL


def _generate(prompt: str, timeout: int = 60) -> str:
    """Call Ollama /api/generate and return the response text."""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "temperature": 0.3},
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception:
        pass
    return ""


def summarize(text: str, max_chars: int = 150) -> str:
    """Return a short summary (falls back to truncation)."""
    if not text:
        return ""
    result = _generate(f"Summarize this in {max_chars} characters or less:\n{text[:1000]}", timeout=30)
    return result or text[:max_chars]


def extract_keywords(text: str, n: int = 5) -> List[str]:
    """Return up to *n* keywords extracted by the LLM."""
    if not text:
        return []
    prompt = (
        f"List {n} important keywords from the following text. "
        f"Only output a comma-separated list of keywords, nothing else:\n{text[:500]}"
    )
    raw = _generate(prompt, timeout=60)
    if not raw:
        return []
    # robust parsing
    raw = raw.replace("\n", ",").replace("*", "").replace("-", ",")
    keywords = [k.strip().strip(".") for k in raw.split(",")]
    keywords = [k for k in keywords if k and len(k) < 50]
    return keywords[:n]
