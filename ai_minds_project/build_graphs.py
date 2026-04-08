"""Build two types of memory graphs: keyword-based (logical) and semantic-based."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import networkx as nx
import numpy as np
from qdrant_client import QdrantClient

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import OUTPUT_DIR


def load_csv_data() -> List[Dict]:
    """Load document metadata from CSV for keyword graph."""
    csv_path = OUTPUT_DIR / "metadata_embeddings.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing: {csv_path}")

    documents = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                doc_id_str = row.get("doc_id", "0")
                # Skip merge conflict markers
                if "<<<<<<" in doc_id_str or ">>>>>>" in doc_id_str or "======" in doc_id_str:
                    continue
                doc_id = int(doc_id_str)
                keywords_str = row.get("keywords", "")
                # Parse keywords - they may contain newlines and commas
                keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
                
                documents.append({
                    "id": doc_id,
                    "file_name": row.get("file_name"),
                    "file_path": row.get("file_path"),
                    "modality": row.get("modality"),
                    "keywords": keywords,
                    "summary": row.get("summary", ""),
                })
            except (ValueError, KeyError) as e:
                # Skip malformed rows
                continue
    
    return documents


def load_qdrant_embeddings(client: QdrantClient, collection: str) -> Dict[int, List[float]]:
    """Load embeddings from Qdrant for semantic graph."""
    # Scroll through all points
    points, next_offset = client.scroll(
        collection_name=collection,
        limit=10000,
        with_payload=True,
        with_vectors=True,
    )
    
    # Group by doc_id and take first chunk embedding as doc representation
    doc_embeddings = {}
    for point in points:
        payload = point.payload or {}
        doc_id = payload.get("doc_id")
        chunk_index = payload.get("chunk_index", 0)
        
        if doc_id and chunk_index == 0:  # Only use first chunk
            doc_embeddings[doc_id] = point.vector
    
    return doc_embeddings


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


def build_keyword_graph(documents: List[Dict], threshold: float = 0.0) -> nx.Graph:
    """Build graph with edges based on shared keywords (logical connections)."""
    G = nx.Graph()

    # Add nodes
    for doc in documents:
        doc_id = doc.get("id")
        keywords = doc.get("keywords", [])
        G.add_node(
            doc_id,
            file_name=doc.get("file_name"),
            file_path=doc.get("file_path"),
            modality=doc.get("modality"),
            keywords=keywords,
            summary=doc.get("summary", ""),
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
    documents: List[Dict],
    doc_embeddings: Dict[int, List[float]],
    threshold: float = 0.5,
    max_edges_per_node: int = 10,
) -> nx.Graph:
    """Build graph with edges based on embedding similarity from Qdrant (semantic connections)."""
    G = nx.Graph()

    # Add nodes
    for doc in documents:
        doc_id = doc.get("id")
        keywords = doc.get("keywords", [])
        G.add_node(
            doc_id,
            file_name=doc.get("file_name"),
            file_path=doc.get("file_path"),
            modality=doc.get("modality"),
            keywords=keywords,
            summary=doc.get("summary", ""),
        )

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

    # Load data from CSV
    print("\n📂 Loading documents from CSV...")
    documents = load_csv_data()
    print(f"✓ Loaded {len(documents)} documents")

    # Build keyword graph
    print("\n🔗 Building keyword-based (logical) graph...")
    keyword_graph = build_keyword_graph(documents, threshold=0.0)
    keyword_output = OUTPUT_DIR / "keyword_graph.json"
    export_graph(keyword_graph, keyword_output)
    print(f"✓ Saved to: {keyword_output}")
    print_graph_stats(keyword_graph, "Keyword-Based")

    # Load embeddings from Qdrant
    print("\n📥 Loading embeddings from Qdrant...")
    client = QdrantClient(host="127.0.0.1", port=6333)
    collection = "ai_minds_embeddings"
    doc_embeddings = load_qdrant_embeddings(client, collection)
    print(f"✓ Loaded {len(doc_embeddings)} document embeddings")

    # Build semantic graph
    print("\n🌐 Building semantic-based graph...")
    semantic_graph = build_semantic_graph(documents, doc_embeddings, threshold=0.5, max_edges_per_node=10)
    semantic_output = OUTPUT_DIR / "semantic_graph.json"
    export_graph(semantic_graph, semantic_output)
    print(f"✓ Saved to: {semantic_output}")
    print_graph_stats(semantic_graph, "Semantic-Based")

    print(f"\n{'='*60}")
    print("✅ Graph construction complete!")
    print('='*60)


if __name__ == "__main__":
    main()
