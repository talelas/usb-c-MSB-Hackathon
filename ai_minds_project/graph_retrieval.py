"""Graph-augmented retrieval with temporal reasoning and weighted scoring."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Set

import networkx as nx
import numpy as np
from qdrant_client import QdrantClient

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import OUTPUT_DIR, EMBEDDING_MODEL
from embedders.embedder import HuggingFaceEmbedder
from temporal_ranking import TemporalRanker


def load_graphs() -> Tuple[nx.Graph, nx.Graph]:
    """Load keyword and semantic graphs."""
    keyword_path = OUTPUT_DIR / "keyword_graph.json"
    semantic_path = OUTPUT_DIR / "semantic_graph.json"
    
    if not keyword_path.exists() or not semantic_path.exists():
        raise FileNotFoundError("Run build_graphs.py first to generate graph files")
    
    with open(keyword_path, "r", encoding="utf-8") as f:
        keyword_data = json.load(f)
    
    with open(semantic_path, "r", encoding="utf-8") as f:
        semantic_data = json.load(f)
    
    # Rebuild NetworkX graphs
    keyword_graph = nx.Graph()
    for node in keyword_data["nodes"]:
        keyword_graph.add_node(node["id"], **node)
    for edge in keyword_data["edges"]:
        keyword_graph.add_edge(edge["source"], edge["target"], weight=edge["weight"])
    
    semantic_graph = nx.Graph()
    for node in semantic_data["nodes"]:
        semantic_graph.add_node(node["id"], **node)
    for edge in semantic_data["edges"]:
        semantic_graph.add_edge(edge["source"], edge["target"], weight=edge["weight"])
    
    return keyword_graph, semantic_graph


def temporal_score(timestamp_str: str, decay_lambda: float = 0.0001) -> float:
    """
    Calculate temporal score with exponential decay.
    
    recency_score = e^(-λ * time_difference)
    
    Args:
        timestamp_str: ISO timestamp string
        decay_lambda: Decay rate (smaller = slower decay)
    
    Returns:
        Score between 0 and 1 (1 = most recent)
    """
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
        time_diff_hours = (now - timestamp).total_seconds() / 3600
        score = np.exp(-decay_lambda * time_diff_hours)
        return float(score)
    except Exception:
        return 0.5  # Neutral score if timestamp missing


def graph_centrality_score(
    doc_id: int,
    keyword_graph: nx.Graph,
    semantic_graph: nx.Graph,
    keyword_weight: float = 0.3,
    semantic_weight: float = 0.7,
) -> float:
    """
    Calculate graph centrality score combining keyword and semantic graphs.
    
    Uses degree centrality (normalized by max degree in graph).
    
    Args:
        doc_id: Document ID
        keyword_graph: Keyword-based graph
        semantic_graph: Semantic-based graph
        keyword_weight: Weight for keyword graph contribution
        semantic_weight: Weight for semantic graph contribution
    
    Returns:
        Combined centrality score
    """
    keyword_centrality = 0.0
    semantic_centrality = 0.0
    
    if doc_id in keyword_graph.nodes():
        degree = keyword_graph.degree(doc_id)
        max_degree = max(dict(keyword_graph.degree()).values()) if keyword_graph.number_of_nodes() > 0 else 1
        keyword_centrality = degree / max_degree if max_degree > 0 else 0.0
    
    if doc_id in semantic_graph.nodes():
        degree = semantic_graph.degree(doc_id)
        max_degree = max(dict(semantic_graph.degree()).values()) if semantic_graph.number_of_nodes() > 0 else 1
        semantic_centrality = degree / max_degree if max_degree > 0 else 0.0
    
    return keyword_weight * keyword_centrality + semantic_weight * semantic_centrality


def expand_graph_neighborhood(
    initial_nodes: Set[int],
    keyword_graph: nx.Graph,
    semantic_graph: nx.Graph,
    max_hops: int = 2,
) -> Set[int]:
    """
    Expand node set by traversing graph neighborhood.
    
    Args:
        initial_nodes: Starting node IDs
        keyword_graph: Keyword-based graph
        semantic_graph: Semantic-based graph
        max_hops: Maximum hops from initial nodes
    
    Returns:
        Expanded set of node IDs
    """
    expanded = set(initial_nodes)
    
    for node in initial_nodes:
        # Expand in keyword graph
        if node in keyword_graph.nodes():
            for hop in range(1, max_hops + 1):
                neighbors = nx.single_source_shortest_path_length(keyword_graph, node, cutoff=hop)
                expanded.update(neighbors.keys())
        
        # Expand in semantic graph
        if node in semantic_graph.nodes():
            for hop in range(1, max_hops + 1):
                neighbors = nx.single_source_shortest_path_length(semantic_graph, node, cutoff=hop)
                expanded.update(neighbors.keys())
    
    return expanded


def get_doc_metadata(doc_id: int, keyword_graph: nx.Graph) -> Dict:
    """Get document metadata from graph nodes."""
    if doc_id in keyword_graph.nodes():
        return dict(keyword_graph.nodes[doc_id])
    return {}


def retrieve_with_graphs(
    query: str,
    client: QdrantClient,
    collection: str,
    keyword_graph: nx.Graph,
    semantic_graph: nx.Graph,
    temporal_ranker: TemporalRanker,
    alpha: float = 0.5,  # Semantic similarity weight
    beta: float = 0.2,   # Graph centrality weight
    gamma: float = 0.2,  # Recency weight
    delta: float = 0.1,  # Importance weight
    initial_k: int = 20,
    final_k: int = 10,
    expand_hops: int = 2,
) -> List[Dict]:
    """
    Retrieve documents using graph-augmented semantic search.
    
    Score = α*semantic_similarity + β*graph_centrality + γ*recency + δ*importance
    
    Args:
        query: Search query text
        client: Qdrant client
        collection: Collection name
        keyword_graph: Keyword-based graph
        semantic_graph: Semantic-based graph
        temporal_ranker: TemporalRanker instance for temporal/importance scores
        alpha: Weight for semantic similarity
        beta: Weight for graph centrality
        gamma: Weight for recency/temporal score
        delta: Weight for importance score
        initial_k: Initial Qdrant retrieval size
        final_k: Final result count
        expand_hops: Graph expansion hops
    
    Returns:
        List of ranked documents with scores
    """
    # Step 1: Semantic retrieval from Qdrant
    embedder = HuggingFaceEmbedder(EMBEDDING_MODEL)
    query_vector = embedder.embed(query).tolist()
    
    response = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=initial_k,
    )
    
    # Extract doc IDs and semantic scores
    initial_results = {}
    for point in response.points:
        payload = point.payload or {}
        doc_id = payload.get("doc_id")
        if doc_id:
            initial_results[doc_id] = {
                "semantic_score": point.score,
                "file_name": payload.get("file_name"),
                "file_path": payload.get("file_path"),
                "modality": payload.get("modality"),
            }
            # Record query match for importance tracking
            temporal_ranker.update_query_match(doc_id)
    
    # Step 2: Graph expansion
    initial_nodes = set(initial_results.keys())
    expanded_nodes = expand_graph_neighborhood(
        initial_nodes, keyword_graph, semantic_graph, max_hops=expand_hops
    )
    
    # Step 3: Score all nodes (initial + expanded)
    all_scores = []
    
    for doc_id in expanded_nodes:
        # Get metadata
        meta = initial_results.get(doc_id, {})
        if not meta:
            # Expanded node not in initial Qdrant results
            graph_meta = get_doc_metadata(doc_id, keyword_graph)
            meta = {
                "semantic_score": 0.0,  # No direct semantic match
                "file_name": graph_meta.get("file_name"),
                "file_path": graph_meta.get("file_path"),
                "modality": graph_meta.get("modality"),
            }
        
        # Compute component scores
        semantic_score = meta.get("semantic_score", 0.0)
        centrality_score = graph_centrality_score(doc_id, keyword_graph, semantic_graph)
        
        # Temporal and importance scores from TemporalRanker
        temporal = temporal_ranker.recency_score(doc_id)
        importance = temporal_ranker.importance_score(doc_id)
        
        # Combined score
        final_score = (
            alpha * semantic_score +
            beta * centrality_score +
            gamma * temporal +
            delta * importance
        )
        
        all_scores.append({
            "doc_id": doc_id,
            "file_name": meta.get("file_name"),
            "file_path": meta.get("file_path"),
            "modality": meta.get("modality"),
            "final_score": final_score,
            "semantic_score": semantic_score,
            "centrality_score": centrality_score,
            "temporal_score": temporal,
            "importance_score": importance,
        })
    
    # Step 4: Rank and return top-k
    all_scores.sort(key=lambda x: x["final_score"], reverse=True)
    return all_scores[:final_k]


def main() -> None:
    parser = argparse.ArgumentParser(description="Graph-augmented retrieval")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6333)
    parser.add_argument("--collection", default="ai_minds_embeddings")
    parser.add_argument("--alpha", type=float, default=0.5, help="Semantic weight")
    parser.add_argument("--beta", type=float, default=0.2, help="Graph centrality weight")
    parser.add_argument("--gamma", type=float, default=0.2, help="Recency weight")
    parser.add_argument("--delta", type=float, default=0.1, help="Importance weight")
    parser.add_argument("--limit", type=int, default=10, help="Number of results")
    args = parser.parse_args()
    
    print("🔍 AI Minds - Graph-Augmented Retrieval")
    print("="*60)
    
    # Load graphs
    print("\n📊 Loading graphs...")
    keyword_graph, semantic_graph = load_graphs()
    print(f"✓ Loaded keyword graph: {keyword_graph.number_of_nodes()} nodes")
    print(f"✓ Loaded semantic graph: {semantic_graph.number_of_nodes()} nodes")
    
    # Connect to Qdrant
    print(f"\n🔗 Connecting to Qdrant at {args.host}:{args.port}...")
    client = QdrantClient(host=args.host, port=args.port)
    
    # Initialize temporal ranker
    print("\n⏰ Initializing temporal ranker...")
    temporal_ranker = TemporalRanker(cache_file=OUTPUT_DIR / "temporal_cache.json")
    
    # Retrieve
    print(f"\n🔎 Query: {args.query}")
    print(f"   Weights: α={args.alpha} β={args.beta} γ={args.gamma} δ={args.delta}")
    
    results = retrieve_with_graphs(
        query=args.query,
        client=client,
        collection=args.collection,
        keyword_graph=keyword_graph,
        semantic_graph=semantic_graph,
        temporal_ranker=temporal_ranker,
        alpha=args.alpha,
        beta=args.beta,
        gamma=args.gamma,
        delta=args.delta,
        final_k=args.limit,
    )
    
    # Display results
    print(f"\n{'='*60}")
    print(f"📋 Top {len(results)} Results")
    print('='*60)
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['file_name']} (score={result['final_score']:.4f})")
        print(f"   Path: {result['file_path']}")
        print(f"   Modality: {result['modality']}")
        print(f"   Breakdown: semantic={result['semantic_score']:.3f} "
              f"centrality={result['centrality_score']:.3f} "
              f"temporal={result['temporal_score']:.3f} "
              f"importance={result['importance_score']:.3f}")
        
        # Record access for temporal tracking
        temporal_ranker.update_access(result['doc_id'])
    
    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
