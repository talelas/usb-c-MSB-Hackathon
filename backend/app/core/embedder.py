"""HuggingFace sentence-transformer embeddings."""
from __future__ import annotations

from functools import lru_cache
from typing import List

import numpy as np

from app.config import EMBEDDING_MODEL, EMBEDDING_DIMENSION


class Embedder:
    """Thin wrapper around SentenceTransformer.

    A module-level factory (:func:`get_embedder`) caches the instance so the
    heavy model is loaded only once per process.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dimension: int = self.model.get_sentence_embedding_dimension()

    # ── public API ───────────────────────────────────────────
    def embed(self, text: str) -> np.ndarray:
        """Return 1-D embedding for a single string."""
        if not text or not text.strip():
            return np.zeros(self.dimension)
        return self.model.encode(text)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Return (N, dim) array for a list of strings."""
        if not texts:
            return np.array([])
        return self.model.encode(texts)


@lru_cache(maxsize=1)
def get_embedder(model_name: str = EMBEDDING_MODEL) -> Embedder:
    """Return the singleton :class:`Embedder` (model loaded once)."""
    return Embedder(model_name)
