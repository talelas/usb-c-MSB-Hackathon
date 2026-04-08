# Memoir Frontend (Vite + React)

Interactive constellation-graph UI for exploring and chatting with your Memoir knowledge base.

→ **See the [root README](../README.md) for the full project overview.**

---

## Structure

```
ui/
├── src/
│   ├── main.jsx                 # React entry-point
│   ├── App.jsx                  # Main app shell + routing
│   ├── ConstellationGraph.jsx   # D3 knowledge graph visualisation
│   ├── index.css                # Global styles
│   ├── components/              # UI components
│   ├── data/                    # Static/mock data
│   └── assets/                  # Images, icons
├── public/                      # Static public assets
├── index.html
├── vite.config.js
├── eslint.config.js
├── package.json
├── .env.example
└── .env                         # git-ignored
```

---

## Features

### 📊 Document Visualization
- **Interactive Graph**: Documents displayed as nodes connected by keyword and semantic relationships.
- **Real-time Data**: Fetches documents dynamically from the backend on load.
- **File Tree**: Hierarchical view of documents grouped by their directory structure.
- **Importance Scoring**: Visual indicators showing document relevance and density.

### 🔍 Search
The search bar provides two seamlessly integrated modes:
1. **Local Autocomplete**: Instant filtering of document names as you type.
2. **Semantic Search**: Submitting the query performs a backend semantic search using the graph-augmented retrieval system. Results display relevance scores and interactive links.

### 💬 AI Chat (RAG)
An integrated chat panel provides an intelligent conversational assistant:
- **Conversational AI**: Engage with your documents through natural language.
- **Context-Aware**: Uses Retrieval-Augmented Generation (RAG) to fetch relevant context from the knowledge base before answering.
- **Source Citations**: Displays which specific documents were used to generate the responses.
- **Persistent History**: Conversation history is maintained per session.

### 📄 Document Details
Interacting with any node or file reveals deep insights:
- Document preview and summarized content.
- Extracted keywords and related semantic terms.
- Connected documents and relationship strength.
- Comprehensive file metadata.

---

## Quick Start

```bash
npm install
cp .env.example .env   # set VITE_API_BASE=http://localhost:8000/api
npm run dev
```

Frontend → **http://localhost:5173**

> Make sure the backend is running on port 8000 first.

---

## Troubleshooting & Debugging

If you encounter issues such as failing to load documents, failed search, or unresponsive chat, please verify the following:
- Ensure the backend server is running and accessible.
- Verify that documents are successfully ingested and the data graph has been built on the backend.
- Check the browser developer console for detailed logs regarding API initialization, component mounting, and request/response payloads.
- Ensure the AI model infrastructure (e.g. Ollama) is active and the specific models are pulled.
