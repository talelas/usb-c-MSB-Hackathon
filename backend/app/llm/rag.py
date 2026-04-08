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


def filter_relevant_documents(
    query: str,
    results: List[Dict],
    *,
    verify_relevance: bool = False,
    min_confidence: float = 0.0,
) -> List[Dict]:
    """Filter retrieved documents based on relevance verification.
    
    Parameters
    ----------
    query : str
        The user's query.
    results : list[dict]
        Retrieved documents from the retrieval system.
    verify_relevance : bool
        Whether to use LLM to verify each document's relevance.
    min_confidence : float
        Minimum score threshold (0-1) to keep a document even without LLM verification.
    
    Returns
    -------
    list[dict]
        Filtered list of relevant documents.
    """
    if not results:
        return results
    
    filtered = []
    
    for result in results:
        # Always keep high-confidence results
        if result.get("final_score", 0) >= min_confidence and min_confidence > 0:
            filtered.append(result)
            continue
        
        # Skip verification if not enabled
        if not verify_relevance:
            filtered.append(result)
            continue
        
        # Verify relevance using LLM
        doc_text = result.get("chunk_text") or result.get("summary", "")
        if not doc_text:
            continue
        
        try:
            is_relevant = llm.verify_relevance(query, doc_text)
            if is_relevant:
                result["verified"] = True
                filtered.append(result)
            else:
                log.debug(
                    "Document filtered as irrelevant | doc_id=%s | score=%.3f",
                    result.get("doc_id"),
                    result.get("final_score", 0),
                )
        except Exception as e:
            log.warning("Relevance verification failed: %s", e)
            # On error, keep the document (fail-open)
            filtered.append(result)
    
    log.info(
        "Filtered documents | original=%d | relevant=%d | verify_enabled=%s",
        len(results),
        len(filtered),
        verify_relevance,
    )
    
    return filtered


def answer(
    query: str,
    kw_graph: nx.Graph,
    sem_graph: nx.Graph,
    *,
    session_id: str = "default",
    top_k: int = 10,
    history_turns: int = 10,
    temperature: float = 0.5,  # Lower temp = more focused/deterministic
    verify_relevance: bool = False,  # Enable LLM-based relevance verification
    min_confidence: float = 0.5,  # Minimum score to skip verification
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
    verify_relevance : bool
        Whether to use LLM to verify document relevance before using them.
    min_confidence : float
        Minimum retrieval score to automatically keep a document (0-1).
        Documents below this will be verified if verify_relevance=True.

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

    # 2.5. Filter documents by relevance (optional)
    if verify_relevance or min_confidence > 0:
        results = filter_relevant_documents(
            query,
            results,
            verify_relevance=verify_relevance,
            min_confidence=min_confidence,
        )
    
    # Handle case where all documents were filtered out
    if not results:
        log.warning("All documents filtered as irrelevant | session=%s", session_id)
        return {
            "answer": "I couldn't find any relevant documents to answer your question. Please try rephrasing or asking about a different topic.",
            "sources": [],
            "session_id": session_id,
        }

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
