# RAG Document Relevance Verification

## Overview

The RAG system now includes an optional **document relevance verification** feature that uses the LLM to verify whether retrieved documents are actually relevant to the user's query before using them to generate an answer.

This helps filter out false positives from the retrieval system and improves answer quality when the retrieved documents may not always be relevant.

## How It Works

1. **Retrieval**: The system retrieves documents using hybrid graph-augmented retrieval (semantic + keyword + graph)
2. **Verification** (optional): Each retrieved document is sent to the LLM with a verification prompt asking "Is this document relevant to answering the query?"
3. **Filtering**: Documents marked as "no" are filtered out
4. **Generation**: Only verified relevant documents are used to generate the final answer

## API Usage

### Basic Usage (No Verification - Default)

```json
POST /api/chat
{
  "query": "What is machine learning?",
  "session_id": "my_session",
  "top_k": 10,
  "temperature": 0.5
}
```

### With Relevance Verification

```json
POST /api/chat
{
  "query": "What is machine learning?",
  "session_id": "my_session",
  "top_k": 10,
  "temperature": 0.5,
  "verify_relevance": true,
  "min_confidence": 0.5
}
```

### Parameters

- **`verify_relevance`** (bool, default: `false`): Enable LLM-based document relevance verification
- **`min_confidence`** (float, 0-1, default: `0.5`): Documents with scores above this threshold are automatically kept. Documents below are verified if `verify_relevance=true`

### Strategy Examples

**Strategy 1: Strict verification (recommended for noisy data)**
```json
{
  "verify_relevance": true,
  "min_confidence": 0.3
}
```
Most documents will be verified. Only very high-scoring documents skip verification.

**Strategy 2: Trust high scores**
```json
{
  "verify_relevance": true,
  "min_confidence": 0.7
}
```
High-confidence documents are trusted. Lower-scoring documents are verified.

**Strategy 3: Verify everything**
```json
{
  "verify_relevance": true,
  "min_confidence": 0.0
}
```
Every document goes through LLM verification (slower but most accurate).

## Python Usage

### Direct Verification Function

You can also use the verification function directly in your code:

```python
from app.llm.ollama_client import verify_relevance

query = "What is neural network?"
document = "A neural network is a computational model inspired by..."

is_relevant = verify_relevance(query, document)
# Returns: True or False
```

### In RAG Pipeline

```python
from app.llm.rag import answer
from app.graph.builder import load_all

kw_graph, sem_graph = load_all()

result = answer(
    query="What is machine learning?",
    kw_graph=kw_graph,
    sem_graph=sem_graph,
    verify_relevance=True,  # Enable verification
    min_confidence=0.5,      # Threshold
    top_k=10,
)

print(result["answer"])
print(f"Used {len(result['sources'])} verified documents")
```

## Performance Considerations

### Pros
- **Better Quality**: Filters out irrelevant documents that might confuse the LLM
- **More Accurate**: Reduces hallucinations from weakly-related context
- **Flexible**: Configurable threshold allows you to balance quality vs. speed

### Cons
- **Slower**: Each verification requires an LLM call (though it's a fast generation)
- **Token Usage**: More LLM calls = more tokens consumed
- **Cost**: If using a paid LLM API, this increases costs

### Optimization Tips

1. **Use appropriate min_confidence**: Set it higher (0.7-0.8) to only verify low-scoring documents
2. **Limit top_k**: Retrieve fewer documents if verification is slow
3. **Batch verification**: For production, consider implementing batch verification
4. **Cache results**: Store verification results for frequently accessed documents

## Verification Prompt

The system uses this prompt to verify relevance:

```
You are a document relevance verifier. Your task is to determine if a 
document is relevant to answer a user's query.

Guidelines:
- Analyze whether the document contains information that helps answer the query.
- Consider semantic relevance, not just keyword matching.
- Be strict: only mark as relevant if the document genuinely helps answer the query.
- Respond with ONLY 'yes' or 'no' - no explanation needed.

Query: {query}

Document:
{document}

Is this document relevant to answering the query? (yes/no):
```

## Example Results

**Query**: "How do neural networks learn?"

**Without Verification**: 5 documents retrieved (scores: 0.72, 0.65, 0.58, 0.42, 0.39)
- Document 4 (score 0.42) talks about network infrastructure (not AI)
- Document 5 (score 0.39) discusses biological neurons (marginally relevant)

**With Verification** (`verify_relevance=true`, `min_confidence=0.6`):
- Docs 1-3 (scores ≥ 0.6) → auto-kept (skipped verification)
- Doc 4 → verified → **filtered out** (not relevant)
- Doc 5 → verified → **kept** (relevant enough)
- Final: 4 documents used

Result: Cleaner context leads to more focused answer.

## Integration in Production

For production deployments, consider:

1. **Toggle per session**: Let users enable/disable verification
2. **Smart defaults**: Enable by default for complex queries
3. **Monitoring**: Log verification results to tune thresholds
4. **Feedback loop**: Use user feedback to improve verification accuracy

## Troubleshooting

**All documents filtered out**:
- Your `min_confidence` might be too low with `verify_relevance=true`
- Your query might not match your document corpus
- Try increasing `top_k` to retrieve more candidates

**Verification too slow**:
- Increase `min_confidence` to reduce verification calls
- Reduce `top_k` to verify fewer documents
- Consider using a faster LLM model

**Inconsistent results**:
- The verification uses `temperature=0.1` for consistency
- If still inconsistent, your documents might be edge cases
- Consider adjusting the verification prompt

## Future Enhancements

Potential improvements:
- **Batch verification**: Verify multiple documents in one call
- **Confidence scores**: Return relevance confidence (not just yes/no)
- **Explain filtering**: Return reasons why documents were filtered
- **Learning**: Fine-tune verification based on user feedback
- **Async verification**: Non-blocking verification for better performance
