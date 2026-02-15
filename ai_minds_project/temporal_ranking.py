"""Temporal reasoning and importance scoring for document ranking."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


class TemporalRanker:
    """Manages temporal decay and importance scores for documents."""
    
    def __init__(self, cache_file: Path = Path("output/temporal_cache.json")):
        """
        Initialize temporal ranker.
        
        Args:
            cache_file: Path to temporal metadata cache
        """
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Load temporal metadata from cache."""
        if self.cache_file.exists():
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "documents": {},  # doc_id -> metadata
            "queries": {},    # query -> metadata
            "last_updated": datetime.now().isoformat(),
        }
    
    def _save_cache(self) -> None:
        """Save temporal metadata to cache."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache["last_updated"] = datetime.now().isoformat()
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
    
    def get_doc_metadata(self, doc_id: int) -> Dict:
        """Get or initialize document temporal metadata."""
        doc_id_str = str(doc_id)
        if doc_id_str not in self.cache["documents"]:
            self.cache["documents"][doc_id_str] = {
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
                "access_count": 0,
                "query_matches": 0,
                "importance_score": 0.5,  # Neutral initial importance
            }
        return self.cache["documents"][doc_id_str]
    
    def recency_score(
        self,
        doc_id: int,
        decay_lambda: float = 0.0001,
        use_created: bool = True,
    ) -> float:
        """
        Calculate recency score with exponential decay.
        
        Score = e^(-λ * time_difference_hours)
        
        Args:
            doc_id: Document ID
            decay_lambda: Decay rate (smaller = slower decay)
                         Default 0.0001 → half-life ≈ 6900 hours (287 days)
            use_created: If True, use creation time. Otherwise use last access time.
        
        Returns:
            Score between 0 and 1 (1 = most recent)
        """
        meta = self.get_doc_metadata(doc_id)
        
        timestamp_key = "created_at" if use_created else "last_accessed"
        timestamp_str = meta.get(timestamp_key)
        
        if not timestamp_str:
            return 0.5  # Neutral if no timestamp
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            time_diff_hours = (now - timestamp).total_seconds() / 3600
            score = np.exp(-decay_lambda * time_diff_hours)
            return float(score)
        except Exception:
            return 0.5
    
    def importance_score(
        self,
        doc_id: int,
        access_weight: float = 0.3,
        query_match_weight: float = 0.7,
    ) -> float:
        """
        Calculate importance score based on usage patterns.
        
        Importance = access_weight * normalized_access_count
                   + query_match_weight * normalized_query_matches
        
        Args:
            doc_id: Document ID
            access_weight: Weight for access frequency
            query_match_weight: Weight for query match frequency
        
        Returns:
            Score between 0 and 1
        """
        meta = self.get_doc_metadata(doc_id)
        
        # Get max values for normalization
        all_docs = self.cache["documents"].values()
        max_access = max((d.get("access_count", 0) for d in all_docs), default=1)
        max_matches = max((d.get("query_matches", 0) for d in all_docs), default=1)
        
        # Normalize
        access_norm = meta.get("access_count", 0) / max_access if max_access > 0 else 0
        matches_norm = meta.get("query_matches", 0) / max_matches if max_matches > 0 else 0
        
        # Combine
        score = access_weight * access_norm + query_match_weight * matches_norm
        
        # Blend with stored importance score (for manual adjustments)
        stored_importance = meta.get("importance_score", 0.5)
        return 0.7 * score + 0.3 * stored_importance
    
    def update_access(self, doc_id: int) -> None:
        """Record document access."""
        meta = self.get_doc_metadata(doc_id)
        meta["access_count"] = meta.get("access_count", 0) + 1
        meta["last_accessed"] = datetime.now().isoformat()
        self._save_cache()
    
    def update_query_match(self, doc_id: int) -> None:
        """Record that document matched a query."""
        meta = self.get_doc_metadata(doc_id)
        meta["query_matches"] = meta.get("query_matches", 0) + 1
        self._save_cache()
    
    def set_importance(self, doc_id: int, importance: float) -> None:
        """Manually set document importance score."""
        meta = self.get_doc_metadata(doc_id)
        meta["importance_score"] = max(0.0, min(1.0, importance))
        self._save_cache()
    
    def temporal_decay_adjustment(
        self,
        doc_id: int,
        base_score: float,
        recency_weight: float = 0.3,
    ) -> float:
        """
        Apply temporal decay adjustment to base score.
        
        Adjusted = base_score * (1 + recency_weight * (recency - 0.5))
        
        This increases score for recent docs and decreases for old ones.
        
        Args:
            doc_id: Document ID
            base_score: Original score (e.g., semantic similarity)
            recency_weight: Weight for temporal adjustment
        
        Returns:
            Temporally adjusted score
        """
        recency = self.recency_score(doc_id)
        adjustment = 1 + recency_weight * (recency - 0.5)
        return base_score * adjustment
    
    def get_trending_docs(
        self,
        window_hours: int = 24,
        min_queries: int = 3,
    ) -> List[Dict]:
        """
        Get documents trending in recent window.
        
        Args:
            window_hours: Time window for trend analysis
            min_queries: Minimum query matches to be trending
        
        Returns:
            List of trending doc metadata sorted by trend score
        """
        now = datetime.now()
        window_start = now - timedelta(hours=window_hours)
        
        trending = []
        for doc_id_str, meta in self.cache["documents"].items():
            last_accessed = datetime.fromisoformat(meta.get("last_accessed", "2020-01-01"))
            
            if last_accessed >= window_start and meta.get("query_matches", 0) >= min_queries:
                trend_score = meta.get("query_matches", 0) / window_hours
                trending.append({
                    "doc_id": int(doc_id_str),
                    "trend_score": trend_score,
                    "query_matches": meta.get("query_matches", 0),
                    "last_accessed": meta.get("last_accessed"),
                })
        
        trending.sort(key=lambda x: x["trend_score"], reverse=True)
        return trending


def temporal_boost_func(
    hours_old: float,
    boost_type: str = "exponential",
    **kwargs,
) -> float:
    """
    Flexible temporal boost function.
    
    Args:
        hours_old: Hours since creation/update
        boost_type: Type of decay function
            - "exponential": e^(-λ * t)
            - "linear": max(0, 1 - slope * t)
            - "step": 1.0 if t < threshold else 0.5
            - "sigmoid": 1 / (1 + e^(k * (t - t0)))
        **kwargs: Parameters for specific functions
            exponential: decay_lambda (default 0.0001)
            linear: slope (default 0.0001)
            step: threshold (default 720 hours = 30 days)
            sigmoid: k (steepness, default 0.01), t0 (midpoint, default 720)
    
    Returns:
        Temporal boost score (0-1)
    """
    if boost_type == "exponential":
        decay_lambda = kwargs.get("decay_lambda", 0.0001)
        return float(np.exp(-decay_lambda * hours_old))
    
    elif boost_type == "linear":
        slope = kwargs.get("slope", 0.0001)
        return max(0.0, 1.0 - slope * hours_old)
    
    elif boost_type == "step":
        threshold = kwargs.get("threshold", 720)  # 30 days
        return 1.0 if hours_old < threshold else 0.5
    
    elif boost_type == "sigmoid":
        k = kwargs.get("k", 0.01)
        t0 = kwargs.get("t0", 720)
        return float(1.0 / (1.0 + np.exp(k * (hours_old - t0))))
    
    else:
        return 1.0  # No boost


# Example usage functions
def demonstrate_temporal_ranking():
    """Demonstrate temporal ranking features."""
    ranker = TemporalRanker()
    
    # Simulate document access
    doc_id = 42
    
    print("🕐 Temporal Ranking Demo")
    print("="*60)
    
    # Initial scores
    print(f"\nDocument {doc_id} initial state:")
    print(f"  Recency score: {ranker.recency_score(doc_id):.4f}")
    print(f"  Importance score: {ranker.importance_score(doc_id):.4f}")
    
    # Simulate usage
    print("\n⚡ Simulating usage...")
    for _ in range(5):
        ranker.update_access(doc_id)
        ranker.update_query_match(doc_id)
    
    print(f"\nAfter 5 accesses:")
    print(f"  Recency score: {ranker.recency_score(doc_id):.4f}")
    print(f"  Importance score: {ranker.importance_score(doc_id):.4f}")
    
    # Test temporal boost
    base_score = 0.7
    adjusted = ranker.temporal_decay_adjustment(doc_id, base_score)
    print(f"\nTemporal adjustment:")
    print(f"  Base score: {base_score:.4f}")
    print(f"  Adjusted score: {adjusted:.4f}")
    
    # Show different decay functions
    print("\n📉 Decay function comparison (30 days old):")
    hours = 720
    print(f"  Exponential: {temporal_boost_func(hours, 'exponential'):.4f}")
    print(f"  Linear: {temporal_boost_func(hours, 'linear', slope=0.001):.4f}")
    print(f"  Step: {temporal_boost_func(hours, 'step', threshold=720):.4f}")
    print(f"  Sigmoid: {temporal_boost_func(hours, 'sigmoid'):.4f}")


if __name__ == "__main__":
    demonstrate_temporal_ranking()
