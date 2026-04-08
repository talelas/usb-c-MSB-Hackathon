"""Thin Ollama HTTP wrapper for chat-style generation.

This module handles the *conversational* LLM calls (RAG answers, follow-ups).
For short enrichment tasks (summarise, keywords) see ``app.core.enricher``.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL


def chat(
    messages: List[Dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.7,
    timeout: int = 120,
) -> str:
    """Send a multi-turn chat to Ollama and return the assistant reply.

    Parameters
    ----------
    messages : list[dict]
        OpenAI-style messages: ``[{"role": "system", "content": "..."}, ...]``
    model : str, optional
        Override the default ``OLLAMA_MODEL``.
    temperature : float
        Sampling temperature (0 = deterministic).
    timeout : int
        HTTP timeout in seconds.

    Returns
    -------
    str
        The assistant's reply text, or an empty string on failure.
    """
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model or OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json().get("message", {}).get("content", "").strip()
    except requests.RequestException:
        pass
    return ""


def generate(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.3,
    timeout: int = 60,
) -> str:
    """Single-shot generation (no chat history).

    Convenience wrapper kept here so callers that only need a quick
    one-off generation don't have to build a messages list.
    """
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model or OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except requests.RequestException:
        pass
    return ""


def verify_relevance(
    query: str,
    document_text: str,
    *,
    model: str | None = None,
    temperature: float = 0.1,  # Low temp for consistent yes/no
    timeout: int = 30,
) -> bool:
    """Verify if a document is relevant to a query.
    
    Uses the LLM to determine if the document contains information
    relevant to answering the query.
    
    Parameters
    ----------
    query : str
        The user's query.
    document_text : str
        The document content to verify.
    model : str, optional
        Override the default OLLAMA_MODEL.
    temperature : float
        Low temperature for consistent binary decision.
    timeout : int
        HTTP timeout in seconds.
    
    Returns
    -------
    bool
        True if document is relevant, False otherwise.
    """
    from app.llm.prompts import build_relevance_verification_prompt
    
    prompt = build_relevance_verification_prompt(query, document_text)
    response = generate(prompt, model=model, temperature=temperature, timeout=timeout)
    
    # Parse response - look for yes/no
    response_lower = response.lower().strip()
    
    # Check for explicit yes/no
    if response_lower.startswith("yes"):
        return True
    elif response_lower.startswith("no"):
        return False
    
    # Fallback: check if 'yes' or 'no' appears in response
    if "yes" in response_lower and "no" not in response_lower:
        return True
    elif "no" in response_lower and "yes" not in response_lower:
        return False
    
    # Default to True if uncertain (to avoid over-filtering)
    return True


def is_available() -> bool:
    """Check whether the Ollama server is reachable."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False
