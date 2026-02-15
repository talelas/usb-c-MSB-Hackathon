# Chat API Integration - Debugging Guide

## ✅ What Was Added

Your chat functionality is now fully integrated with the backend API (`POST /api/chat`). Comprehensive logging has been added to help diagnose any issues.

## 🔍 Logging Overview

The following logs will appear in your browser's console (F12 → Console tab):

### 1. API Initialization
```
[API] Initialized with base URL: http://localhost:8000/api
[API] Environment VITE_API_BASE: undefined (or your value)
```

### 2. Chat Panel Mounting
```
[ChatPanel] Component mounted with sessionId: default
[ChatPanel] Loading conversation history for session: default
```

### 3. Sending a Chat Message
```
[ChatPanel] Sending message: what is this about?
[ChatPanel] Session ID: default
[ChatPanel] Calling sendChatMessage API...
[Chat API] Sending chat message: { query: "what is this about?", sessionId: "default", ... }
[Chat API] Request payload: { query: "...", session_id: "...", top_k: 10, ... }
[API] POST http://localhost:8000/api/chat
[API] Request body: { query: "...", session_id: "...", ... }
```

### 4. Successful Response
```
[API] Response status: 200
[API] Response data: { answer: "...", sources: [...], session_id: "..." }
[Chat API] Chat response received: { answer: "...", sources: [...] }
[ChatPanel] Received response: { answer: "...", sources: [...] }
[ChatPanel] Assistant message added to UI
```

### 5. Error Handling
```
[API] Response status: 500 (or other error)
[API] Error response: { detail: "..." }
[API] Request failed for /chat: Error: ...
[Chat API] Chat request failed: Error: ...
[ChatPanel] Error occurred: Error: ...
```

## 🚀 How to Test

### Step 1: Create .env file (if not exists)

```bash
cd ui
echo "VITE_API_BASE=http://localhost:8000/api" > .env
```

### Step 2: Ensure Backend is Running

In one terminal:
```bash
cd ai_minds_project
# Make sure .venv is activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's working:
```bash
curl http://localhost:8000/api/health
```

### Step 3: Start Frontend

In another terminal:
```bash
cd ui
npm run dev
```

### Step 4: Test Chat

1. Open the app in browser (usually http://localhost:5173)
2. Open browser DevTools (F12) → Console tab
3. Click the 💬 button in top-right to open chat
4. Type a message and press Enter or click Send
5. Watch the console logs

## 🔧 Troubleshooting

### Issue: No logs appear

**Check:**
- Browser console is open (F12)
- Console filter is set to show all logs (not just errors)
- Chat panel is actually open (click 💬 button)

### Issue: CORS error in console

```
Access to fetch at 'http://localhost:8000/api/chat' from origin 'http://localhost:5173' has been blocked by CORS
```

**Fix:** Add CORS middleware to backend `app/main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue: 404 Not Found

```
[API] Response status: 404
```

**Check:**
- Backend is running on port 8000
- URL in .env matches backend URL
- Endpoint exists: `POST /api/chat` should be in your FastAPI routes

### Issue: Network Error / Failed to fetch

```
TypeError: Failed to fetch
```

**Check:**
- Backend server is running
- No firewall blocking localhost:8000
- Correct URL in .env file
- Try accessing http://localhost:8000/api/health directly in browser

### Issue: 500 Internal Server Error

```
[API] Response status: 500
```

**Check backend logs for:**
- Database connection issues (Postgres, Qdrant)
- Ollama not running (`ollama serve`)
- Model not pulled (`ollama pull llama3.2`)
- Missing documents (run ingestion first)

### Issue: Response but no answer

```
[Chat API] Chat response received: { answer: "", sources: [] }
```

**Check:**
- Documents are ingested: `curl http://localhost:8000/api/documents`
- Graphs are built: `curl -X POST http://localhost:8000/api/graphs/rebuild`
- Ollama is responding: `ollama list`

## 📊 Expected Flow

For a working setup, you should see this sequence:

1. **App loads** → Logs show API base URL
2. **Documents load** → See `[API] GET /api/documents`
3. **Chat opens** → See `[ChatPanel] Component mounted`
4. **Message sent** → See all the `[ChatPanel]` and `[Chat API]` logs
5. **Response received** → See status 200 and answer displayed in UI

## 🎯 Quick Verification Checklist

```bash
# 1. Check backend health
curl http://localhost:8000/api/health

# 2. Check documents exist
curl http://localhost:8000/api/documents

# 3. Test chat directly
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "session_id": "test"}'

# 4. Check frontend is connecting
# Open browser console and look for:
# "[API] Initialized with base URL: http://localhost:8000/api"
```

## 💡 Common Solutions

### Backend not running
```bash
cd ai_minds_project
source ../.venv/Scripts/activate  # or .venv/bin/activate on Linux/Mac
uvicorn app.main:app --reload
```

### No documents ingested
```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"directory": null, "rebuild_graphs": true}'
```

### Ollama not responding
```bash
ollama serve  # Start Ollama
ollama pull llama3.2  # Pull the model
```

## 📝 What to Report

If you still have issues, share these logs:

1. **Browser console output** (all `[API]`, `[Chat API]`, `[ChatPanel]` logs)
2. **Backend terminal output** (FastAPI server logs)
3. **Network tab** (F12 → Network → filter by "chat")
4. **Backend health check**:
   ```bash
   curl http://localhost:8000/api/health | json_pp
   ```

The detailed logging will show exactly where the issue occurs!
