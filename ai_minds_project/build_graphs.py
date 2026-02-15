"""Build two types of memory graphs: keyword-based (logical) and semantic-based."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import networkx as nx
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import OUTPUT_DIR


def load_data() -> List[Dict]:
    """Load document metadata and embeddings."""
    meta_path = OUTPUT_DIR / "metadata_embeddings.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing: {meta_path}")

    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("documents", [])


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    dot = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def jaccard_similarity(set1: set, set2: set) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def build_keyword_graph(documents: List[Dict], threshold: float = 0.1) -> nx.Graph:
    """Build graph with edges based on shared keywords (logical connections)."""
    G = nx.Graph()

    # Add nodes
    for doc in documents:
        doc_id = doc.get("id")
        file_meta = doc.get("file_metadata", {})
        keywords = doc.get("keywords", [])
        G.add_node(
            doc_id,
            file_name=file_meta.get("file_name"),
            file_path=file_meta.get("file_path"),
            modality=file_meta.get("modality"),
            keywords=keywords,
            summary=doc.get("text_summary", ""),
        )

    # Add edges based on keyword overlap
    doc_list = list(documents)
    for i, doc1 in enumerate(doc_list):
        keywords1 = set(kw.lower() for kw in doc1.get("keywords", []))
        doc_id1 = doc1.get("id")

        for doc2 in doc_list[i + 1 :]:
            keywords2 = set(kw.lower() for kw in doc2.get("keywords", []))
            doc_id2 = doc2.get("id")

            similarity = jaccard_similarity(keywords1, keywords2)
            if similarity >= threshold:
                G.add_edge(doc_id1, doc_id2, weight=similarity, edge_type="keyword")

    return G


def build_semantic_graph(
    documents: List[Dict], threshold: float = 0.5, max_edges_per_node: int = 10
) -> nx.Graph:
    """Build graph with edges based on embedding similarity (semantic connections)."""
    G = nx.Graph()

    # Add nodes
    for doc in documents:
        doc_id = doc.get("id")
        file_meta = doc.get("file_metadata", {})
        keywords = doc.get("keywords", [])
        G.add_node(
            doc_id,
            file_name=file_meta.get("file_name"),
            file_path=file_meta.get("file_path"),
            modality=file_meta.get("modality"),
            keywords=keywords,
            summary=doc.get("text_summary", ""),
        )

    # Collect embeddings (use first chunk embedding as document representation)
    doc_embeddings = {}
    for doc in documents:
        doc_id = doc.get("id")
        chunks = doc.get("chunks", [])
        if chunks:
            doc_embeddings[doc_id] = chunks[0].get("embedding", [])

    # Add edges based on embedding similarity
    doc_ids = list(doc_embeddings.keys())
    for i, doc_id1 in enumerate(doc_ids):
        emb1 = doc_embeddings[doc_id1]
        similarities = []

        for doc_id2 in doc_ids[i + 1 :]:
            emb2 = doc_embeddings[doc_id2]
            similarity = cosine_similarity(emb1, emb2)
            if similarity >= threshold:
                similarities.append((doc_id2, similarity))

        # Keep only top-k edges per node to avoid dense graph
        similarities.sort(key=lambda x: x[1], reverse=True)
        for doc_id2, sim in similarities[:max_edges_per_node]:
            G.add_edge(doc_id1, doc_id2, weight=sim, edge_type="semantic")

    return G


def export_graph(G: nx.Graph, output_path: Path) -> None:
    """Export graph to JSON format."""
    graph_data = {
        "nodes": [
            {
                "id": node,
                "file_name": G.nodes[node].get("file_name"),
                "file_path": G.nodes[node].get("file_path"),
                "modality": G.nodes[node].get("modality"),
                "keywords": G.nodes[node].get("keywords"),
                "summary": G.nodes[node].get("summary", "")[:200],
            }
            for node in G.nodes()
        ],
        "edges": [
            {
                "source": u,
                "target": v,
                "weight": data.get("weight"),
                "edge_type": data.get("edge_type"),
            }
            for u, v, data in G.edges(data=True)
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)


def print_graph_stats(G: nx.Graph, name: str) -> None:
    """Print graph statistics."""
    print(f"\n{'='*60}")
    print(f"📊 {name} Graph Statistics")
    print('='*60)
    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")
    print(f"Density: {nx.density(G):.4f}")
    
    if G.number_of_edges() > 0:
        print(f"Average degree: {sum(dict(G.degree()).values()) / G.number_of_nodes():.2f}")
        
        # Top connected nodes
        degrees = dict(G.degree())
        top_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\nTop 5 connected nodes:")
        for node_id, degree in top_nodes:
            file_name = G.nodes[node_id].get("file_name", "unknown")
            print(f"  - {file_name} (degree: {degree})")


def main() -> None:
    print("🧠 AI Minds - Graph Memory Builder")
    print("="*60)

    # Load data
    print("\n📂 Loading documents...")
    documents = load_data()
    print(f"✓ Loaded {len(documents)} documents")

    # Build keyword graph
    print("\n🔗 Building keyword-based (logical) graph...")
    keyword_graph = build_keyword_graph(documents, threshold=0.1)
    keyword_output = OUTPUT_DIR / "keyword_graph.json"
    export_graph(keyword_graph, keyword_output)
    print(f"✓ Saved to: {keyword_output}")
    print_graph_stats(keyword_graph, "Keyword-Based")

    # Build semantic graph
    print("\n🌐 Building semantic-based graph...")
    semantic_graph = build_semantic_graph(documents, threshold=0.5, max_edges_per_node=10)
    semantic_output = OUTPUT_DIR / "semantic_graph.json"
    export_graph(semantic_graph, semantic_output)
    print(f"✓ Saved to: {semantic_output}")
    print_graph_stats(semantic_graph, "Semantic-Based")

    print(f"\n{'='*60}")
    print("✅ Graph construction complete!")
    print('='*60)


if __name__ == "__main__":
    main()
