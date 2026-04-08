"""Redis client for caching, logging, and conversation memory.

Namespaces (key prefixes):
  * ``cache:``  – general-purpose TTL cache (media text, embeddings, etc.)
  * ``log:``    – append-only pipeline log stream
  * ``conv:``   – per-session conversation history (list of messages)
"""
from __future__ import annotations

import json
import time
from typing import Any, List, Optional

import redis

from app.config import REDIS_URL

_pool: redis.ConnectionPool | None = None


def _get_client() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)
    return redis.Redis(connection_pool=_pool)


# ── Generic cache ────────────────────────────────────────────

def cache_get(key: str) -> Optional[str]:
    return _get_client().get(f"cache:{key}")


def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    _get_client().set(f"cache:{key}", value, ex=ttl)


def cache_json_get(key: str) -> Any | None:
    raw = cache_get(key)
    return json.loads(raw) if raw else None


def cache_json_set(key: str, value: Any, ttl: int = 3600) -> None:
    cache_set(key, json.dumps(value, default=str), ttl)


# ── Pipeline logging ─────────────────────────────────────────

def log_event(event: str, data: dict | None = None) -> None:
    """Append a timestamped event to the ``log:pipeline`` stream."""
    entry = {"event": event, "ts": time.time(), **(data or {})}
    _get_client().rpush("log:pipeline", json.dumps(entry, default=str))


def get_logs(last_n: int = 50) -> List[dict]:
    raw = _get_client().lrange("log:pipeline", -last_n, -1)
    return [json.loads(r) for r in raw]


# ── Conversation memory ──────────────────────────────────────

def conversation_key(session_id: str) -> str:
    return f"conv:{session_id}"


def conversation_push(session_id: str, role: str, content: str) -> None:
    """Append a message to the conversation for *session_id*.

    Each message is stored as a JSON object ``{"role": ..., "content": ...}``.
    Conversations expire after 24 h of inactivity.
    """
    r = _get_client()
    key = conversation_key(session_id)
    r.rpush(key, json.dumps({"role": role, "content": content}))
    r.expire(key, 86400)  # 24 h TTL


def conversation_get(session_id: str, last_n: int = 20) -> List[dict]:
    """Return the last *last_n* messages for *session_id*."""
    raw = _get_client().lrange(conversation_key(session_id), -last_n, -1)
    return [json.loads(r) for r in raw]


def conversation_clear(session_id: str) -> None:
    _get_client().delete(conversation_key(session_id))


# ── Media text cache (replaces JSON file cache) ─────────────

def media_cache_get(file_path: str, kind: str) -> Optional[str]:
    """Get cached caption or transcript (kind = 'caption' | 'transcript')."""
    return cache_get(f"media:{kind}:{file_path}")


def media_cache_set(file_path: str, kind: str, text: str, ttl: int = 604800) -> None:
    """Cache caption/transcript for 7 days by default."""
    cache_set(f"media:{kind}:{file_path}", text, ttl)
