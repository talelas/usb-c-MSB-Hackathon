"""Full RAG pipeline: query → retrieve → build prompt → generate.

This is the main entry-point that the API layer calls.
It ties together graph retrieval, conversation memory, and the LLM.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import networkx as nx

from app.db import redis_client as rdb
from app.graph import retrieval as graph_retrieval
from app.llm import ollama_client as llm
from app.llm.prompts import build_rag_messages

log = logging.getLogger(__name__)


def answer(
    query: str,
    kw_graph: nx.Graph,
    sem_graph: nx.Graph,
    *,
    session_id: str = "default",
    top_k: int = 10,
    history_turns: int = 10,
    temperature: float = 0.5,  # Lower temp = more focused/deterministic
) -> Dict[str, Any]:
    """End-to-end RAG: retrieval → prompt assembly → LLM generation.

    Parameters
    ----------
    query : str
        The user's natural-language question.
    kw_graph, sem_graph : nx.Graph
        Pre-built keyword and semantic graphs (see ``app.graph.builder``).
    session_id : str
        Conversation session identifier (for memory retrieval).
    top_k : int
        Number of context chunks to feed the LLM.
    history_turns : int
        How many previous conversation turns to include.
    temperature : float
        LLM sampling temperature.

    Returns
    -------
    dict
        ``{"answer": str, "sources": list[dict], "session_id": str}``
    """
    # 1. Pull conversation history from Redis
    history = rdb.conversation_get(session_id, last_n=history_turns)

    # 2. Graph-augmented retrieval (hybrid: semantic + keyword + graph expansion)
    results = graph_retrieval.retrieve(
        query, 
        kw_graph, 
        sem_graph, 
        final_k=top_k,
        initial_k=top_k * 3,  # Cast wider net for graph expansion
        alpha=0.6,   # Semantic score weight
        beta=0.2,    # Graph centrality weight
        gamma=0.1,   # Temporal/recency weight
        delta=0.1,   # Importance weight
    )

    # 3. Build prompt messages
    messages = build_rag_messages(query, results, history or None)

    # 4. Call LLM
    reply = llm.chat(messages, temperature=temperature)
    if not reply:
        reply = "I'm sorry, I couldn't generate an answer. Please try again."

    # 5. Persist conversation turn
    rdb.conversation_push(session_id, "user", query)
    rdb.conversation_push(session_id, "assistant", reply)

    # 6. Log the event
    rdb.log_event("rag_query", {
        "session_id": session_id,
        "query": query[:200],
        "n_results": len(results),
        "top_score": results[0]["final_score"] if results else 0.0,
    })

    log.info("RAG answer generated | session=%s | sources=%d", session_id, len(results))

    return {
        "answer": reply,
        "sources": [
            {
                "doc_id": r["doc_id"],
                "file_name": r.get("file_name"),
                "modality": r.get("modality"),
                "score": round(r["final_score"], 4),
            }
            for r in results
        ],
        "session_id": session_id,
    }


def get_history(session_id: str, last_n: int = 20) -> List[Dict]:
    """Return the conversation history for a session."""
    return rdb.conversation_get(session_id, last_n=last_n)


def clear_history(session_id: str) -> None:
    """Clear conversation history for a session."""
    rdb.conversation_clear(session_id)
    rdb.log_event("conversation_cleared", {"session_id": session_id})
