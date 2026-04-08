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


def build_keyword_graph(documents: List[Dict], threshold: float = 0.1) -> nx.Graph:
    """Build graph with edges based on shared keywords (logical connections).
    
    Args:
        documents: List of document dictionaries
        threshold: Minimum Jaccard similarity to create edge (default 0.1).
                  Set to 0.0 to include all pairs (even with no overlap).
    """
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
    # Only compare documents that have at least one keyword
    doc_list = [d for d in documents if d.get("keywords")]
    
    for i, doc1 in enumerate(doc_list):
        keywords1 = set(kw.lower() for kw in doc1.get("keywords", []))
        doc_id1 = doc1.get("id")
        
        if not keywords1:  # Skip if empty after processing
            continue

        for doc2 in doc_list[i + 1 :]:
            keywords2 = set(kw.lower() for kw in doc2.get("keywords", []))
            doc_id2 = doc2.get("id")
            
            if not keywords2:  # Skip if empty after processing
                continue

            similarity = jaccard_similarity(keywords1, keywords2)
            if similarity > 0 and similarity >= threshold:  # Only add edges with actual overlap
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
        
        # Edge weight distribution
        weights = [data.get('weight', 0) for _, _, data in G.edges(data=True)]
        zero_weights = sum(1 for w in weights if w == 0.0)
        nonzero_weights = len(weights) - zero_weights
        print(f"\nEdge weights:")
        print(f"  Zero weight (0.0): {zero_weights}")
        print(f"  Non-zero weight: {nonzero_weights}")
        if nonzero_weights > 0:
            print(f"  Min weight: {min(w for w in weights if w > 0):.4f}")
            print(f"  Max weight: {max(weights):.4f}")
            print(f"  Avg weight: {sum(w for w in weights if w > 0) / nonzero_weights:.4f}")
        
        # Top connected nodes
        degrees = dict(G.degree())
        top_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\nTop 5 connected nodes:")
        for node_id, degree in top_nodes:
            file_name = G.nodes[node_id].get("file_name", "unknown")
            print(f"  - {file_name} (degree: {degree})")


def visualize_graph_tree(
    G: nx.Graph, 
    max_nodes: int = 30,
    min_weight: float = 0.1,
    show_weights: bool = True,
) -> None:
    """Visualize graph as tree structure in console.
    
    Args:
        G: NetworkX graph to visualize
        max_nodes: Maximum number of nodes to display
        min_weight: Minimum edge weight to display
        show_weights: Whether to show edge weights
    """
    if G.number_of_nodes() == 0:
        print("\n⚠️  Empty graph - no nodes to visualize")
        return
    
    if G.number_of_edges() == 0:
        print("\n⚠️  No edges in graph - showing isolated nodes:")
        for i, node in enumerate(list(G.nodes())[:max_nodes]):
            file_name = G.nodes[node].get("file_name", f"Node {node}")
            keywords = G.nodes[node].get("keywords", [])
            kw_str = ", ".join(keywords[:3]) if keywords else "no keywords"
            print(f"  • {file_name} ({kw_str})")
        return
    
    print(f"\n{'='*60}")
    print("🌳 Graph Structure (Tree Visualization)")
    print('='*60)
    print(f"Note: Showing nodes with edges weight >= {min_weight}")
    print()
    
    # Filter edges by weight
    filtered_edges = [
        (u, v, data) 
        for u, v, data in G.edges(data=True) 
        if data.get('weight', 0) >= min_weight
    ]
    
    if not filtered_edges:
        print(f"⚠️  No edges with weight >= {min_weight}")
        return
    
    # Build filtered graph
    G_filtered = nx.Graph()
    for u, v, data in filtered_edges:
        G_filtered.add_edge(u, v, **data)
    
    # Find connected components
    components = list(nx.connected_components(G_filtered))
    components.sort(key=len, reverse=True)
    
    print(f"Found {len(components)} connected component(s)\n")
    
    nodes_shown = 0
    for comp_idx, component in enumerate(components):
        if nodes_shown >= max_nodes:
            print(f"\n... (showing only first {max_nodes} nodes)")
            break
        
        component_nodes = list(component)
        if len(component_nodes) < 2:
            continue  # Skip isolated nodes
        
        print(f"Component {comp_idx + 1} ({len(component_nodes)} nodes):")
        print("│")
        
        # Use BFS to traverse component
        subgraph = G_filtered.subgraph(component_nodes)
        start_node = component_nodes[0]
        visited = set()
        queue = [(start_node, 0, True)]  # (node, depth, is_last)
        
        while queue and nodes_shown < max_nodes:
            node, depth, is_last = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            nodes_shown += 1
            
            # Format node info
            file_name = G.nodes[node].get("file_name", f"Node {node}")
            keywords = G.nodes[node].get("keywords", [])
            modality = G.nodes[node].get("modality", "")
            
            # Truncate long names
            if len(file_name) > 40:
                file_name = file_name[:37] + "..."
            
            # Create tree structure
            prefix = "│   " * (depth - 1) + "├── " if depth > 0 else "└── "
            if depth == 0:
                prefix = "└── "
            
            kw_display = f"[{', '.join(keywords[:2])}]" if keywords else "[no kw]"
            
            print(f"{prefix}{file_name} {kw_display} ({modality})")
            
            # Show edges
            neighbors = list(subgraph.neighbors(node))
            for neighbor in neighbors:
                if neighbor not in visited:
                    edge_data = subgraph.get_edge_data(node, neighbor)
                    weight = edge_data.get('weight', 0)
                    if show_weights:
                        edge_prefix = "│   " * depth + "│   ├─"
                        print(f"{edge_prefix}─ weight: {weight:.3f}")
                    queue.append((neighbor, depth + 1, neighbor == neighbors[-1]))
        
        print()
    
    # Show some isolated high-value nodes
    isolated = [n for n in G.nodes() if G.degree(n) == 0 and G.nodes[n].get("keywords")]
    if isolated and nodes_shown < max_nodes:
        print(f"\nIsolated nodes with keywords ({len(isolated)} total, showing {min(5, len(isolated))}):")
        for node in isolated[:5]:
            file_name = G.nodes[node].get("file_name", f"Node {node}")
            keywords = G.nodes[node].get("keywords", [])
            kw_str = ", ".join(keywords[:3]) if keywords else "no keywords"
            print(f"  • {file_name} ({kw_str})")
    
    print(f"\n{'='*60}")


def main() -> None:
    print("🧠 Memoir - Graph Memory Builder")
    print("="*60)

    # Load data from CSV
    print("\n📂 Loading documents from CSV...")
    documents = load_csv_data()
    print(f"✓ Loaded {len(documents)} documents")
    
    # Count documents with/without keywords
    docs_with_kw = sum(1 for d in documents if d.get('keywords'))
    docs_without_kw = len(documents) - docs_with_kw
    print(f"  - With keywords: {docs_with_kw}")
    print(f"  - Without keywords: {docs_without_kw}")

    # Build keyword graph
    print("\n🔗 Building keyword-based (logical) graph...")
    keyword_graph = build_keyword_graph(documents, threshold=0.1)
    keyword_output = OUTPUT_DIR / "keyword_graph.json"
    export_graph(keyword_graph, keyword_output)
    print(f"✓ Saved to: {keyword_output}")
    print_graph_stats(keyword_graph, "Keyword-Based")
    
    # Visualize keyword graph
    visualize_graph_tree(keyword_graph, max_nodes=30, min_weight=0.1)

    # Load embeddings from Qdrant
    print("\n📥 Loading embeddings from Qdrant...")
    client = QdrantClient(host="127.0.0.1", port=6333)
    collection = "memoir_embeddings"
    doc_embeddings = load_qdrant_embeddings(client, collection)
    print(f"✓ Loaded {len(doc_embeddings)} document embeddings")

    # Build semantic graph
    print("\n🌐 Building semantic-based graph...")
    semantic_graph = build_semantic_graph(documents, doc_embeddings, threshold=0.5, max_edges_per_node=10)
    semantic_output = OUTPUT_DIR / "semantic_graph.json"
    export_graph(semantic_graph, semantic_output)
    print(f"✓ Saved to: {semantic_output}")
    print_graph_stats(semantic_graph, "Semantic-Based")
    
    # Visualize semantic graph
    visualize_graph_tree(semantic_graph, max_nodes=30, min_weight=0.5)

    print(f"\n{'='*60}")
    print("✅ Graph construction complete!")
    print('='*60)


if __name__ == "__main__":
    main()
