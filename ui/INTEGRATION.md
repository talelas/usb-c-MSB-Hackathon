# Frontend-Backend Integration Guide

## Overview

The React frontend has been fully integrated with the AI-MINDS backend API. The application now:

- ✅ Fetches real documents from the backend (`GET /api/documents`)
- ✅ Performs semantic search (`POST /api/search`)
- ✅ Supports RAG-powered chat (`POST /api/chat`)
- ✅ Displays search results with relevance scores
- ✅ Shows conversation history
- ✅ Builds interactive graph visualizations from document relationships

## Architecture

```
ui/
├── src/
│   ├── data/
│   │   ├── api.js              # API client for backend communication
│   │   ├── graphTransforms.js   # Transform documents into graph data
│   │   └── theme.js             # Color theme and utilities
│   ├── components/
│   │   ├── ChatPanel.jsx        # RAG chat interface
│   │   ├── SearchBar.jsx        # Search with autocomplete
│   │   ├── LeftSidebar.jsx      # File tree explorer
│   │   ├── RightSidebar.jsx     # Document details & search results
│   │   ├── TopBar.jsx           # Tab management
│   │   └── StatusBar.jsx        # Status information
│   ├── App.jsx                  # Main application
│   └── ConstellationGraph.jsx   # Graph visualization
└── .env                         # Environment configuration
```

## Setup

### 1. Configure API Endpoint

Create a `.env` file in the `ui/` directory:

```bash
VITE_API_BASE=http://localhost:8000/api
```

### 2. Install Dependencies

```bash
cd ui
npm install
```

### 3. Start the Frontend

```bash
npm run dev
```

The UI will be available at `http://localhost:5173` (or the port shown by Vite).

### 4. Ensure Backend is Running

Make sure the backend API server is running:

```bash
cd ../ai_minds_project
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Features

### 📊 Document Visualization

- **Interactive Graph**: Documents displayed as nodes connected by keyword and semantic relationships
- **Real-time Data**: Fetches documents from backend on load
- **File Tree**: Hierarchical view of documents grouped by directory
- **Importance Scoring**: Visual indicators showing document relevance

### 🔍 Search

The search bar supports two modes:

1. **Local Autocomplete**: Instant filtering of document names as you type
2. **Semantic Search**: Press Enter to perform backend semantic search using the graph-augmented retrieval system

```
Type: "machine learning" → Press Enter
```

Results show:
- Document names with file type icons
- Relevance scores (semantic + centrality + temporal + importance)
- Clickable links to view full document details

### 💬 AI Chat (RAG)

Click the 💬 button in the top-right to open the chat panel:

- **Conversational AI**: Ask questions about your documents
- **Context-Aware**: Uses RAG to retrieve relevant context before answering
- **Source Citations**: Shows which documents were used to generate each answer
- **Persistent History**: Conversation history saved per session

Example queries:
```
"What are the main topics in my documents?"
"Summarize the content about neural networks"
"Which documents discuss blockchain?"
```

### 📄 Document Details

Click any node in the graph or file in the tree to view:
- Document preview/summary
- Keywords extracted from content
- Importance score with visual indicator
- Connected documents (relationships)
- File metadata (path, type, etc.)

## API Integration

### API Client (`src/data/api.js`)

The API client provides functions for all backend endpoints:

```javascript
import { fetchDocuments, searchDocuments, sendChatMessage } from './data/api';

// Get all documents
const docs = await fetchDocuments();

// Semantic search
const response = await searchDocuments("machine learning", 10);

// Chat with RAG
const result = await sendChatMessage("What is this about?", "session-123");
```

### Available API Functions

| Function | Endpoint | Description |
|----------|----------|-------------|
| `fetchDocuments()` | `GET /api/documents` | Get all ingested documents |
| `fetchDocument(id)` | `GET /api/documents/{id}` | Get single document |
| `searchDocuments(query, topK)` | `POST /api/search` | Semantic search |
| `sendChatMessage(query, sessionId, options)` | `POST /api/chat` | RAG chat |
| `getConversationHistory(sessionId)` | `GET /api/conversations/{sessionId}` | Get chat history |
| `clearConversation(sessionId)` | `DELETE /api/conversations/{sessionId}` | Clear history |
| `ingestDirectory(dir)` | `POST /api/ingest` | Trigger ingestion |
| `rebuildGraphs()` | `POST /api/graphs/rebuild` | Rebuild graphs |
| `getHealthStatus()` | `GET /api/health` | Service health check |

### Graph Transforms (`src/data/graphTransforms.js`)

Transforms backend document data into graph-ready format:

```javascript
import { buildGraphData, buildNeighborMap } from './data/graphTransforms';

const docs = await fetchDocuments();
const { nodes, links, fileTree } = buildGraphData(docs);
const neighborMap = buildNeighborMap(links);
```

**Node Structure:**
```javascript
{
  id: "file-123",
  docId: 123,
  name: "document.pdf",
  type: "file",
  ext: "pdf",
  group: "data",
  importance: 0.75,
  keywords: ["AI", "ML"],
  summary: "...",
  // ...
}
```

**Link Structure:**
```javascript
{
  source: "file-123",
  target: "file-456",
  value: 0.8,           // Strength (0-1)
  type: "keyword",      // "keyword" or "group"
  keywords: ["AI"],     // Common keywords (if type=keyword)
}
```

## User Workflow

### Typical Usage Flow

1. **Load Documents**: App fetches documents from backend automatically
2. **Browse**: Explore the graph visualization or file tree
3. **Search**: Use the search bar for quick document lookup or semantic search
4. **View Details**: Click documents to see previews, keywords, and connections
5. **Ask Questions**: Open chat panel to interact with documents via AI

### Search Workflow

```
User types "neural" 
  ↓
Local autocomplete shows matching files
  ↓
User presses Enter
  ↓
POST /api/search with query="neural"
  ↓
Backend performs:
  - Semantic embedding
  - Vector search in Qdrant
  - Graph-augmented scoring
  - Ranking by combined score
  ↓
Frontend displays ranked results
  ↓
User clicks result → Document opens in right panel
```

### Chat Workflow

```
User asks "What are cognitive systems?"
  ↓
POST /api/chat with query + session_id
  ↓
Backend RAG pipeline:
  1. Retrieve relevant chunks (graph-augmented)
  2. Optionally verify relevance
  3. Generate answer with context
  4. Return answer + sources
  ↓
Frontend displays answer with source citations
  ↓
Conversation stored in Redis (24h TTL)
```

## Troubleshooting

### "Failed to load documents"

- ✓ Check backend is running on `http://localhost:8000`
- ✓ Verify documents are ingested: `GET http://localhost:8000/api/documents`
- ✓ Check browser console for CORS errors
- ✓ Ensure `.env` has correct `VITE_API_BASE`

### "Search failed"

- ✓ Verify Qdrant is running: `docker ps`
- ✓ Check backend logs for errors
- ✓ Ensure graphs are built: `POST /api/graphs/rebuild`

### "Chat not responding"

- ✓ Check Ollama is running: `ollama list`
- ✓ Ensure model is pulled: `ollama pull llama3.2`
- ✓ Verify backend health: `GET /api/health`

### CORS Issues

If you see CORS errors, ensure the backend `main.py` has:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Development

### Hot Reload

Both frontend and backend support hot reload:

```bash
# Frontend (Vite)
npm run dev

# Backend (uvicorn)
uvicorn app.main:app --reload
```

### Building for Production

```bash
# Build frontend
npm run build

# Serve with a static server
npm run preview
```

The built files will be in `dist/` directory.

## Next Steps

- [ ] Add file upload UI for ingestion
- [ ] Show graph rebuild progress
- [ ] Add conversation session management UI
- [ ] Implement advanced search filters
- [ ] Add document export functionality
- [ ] Enable graph layout customization
