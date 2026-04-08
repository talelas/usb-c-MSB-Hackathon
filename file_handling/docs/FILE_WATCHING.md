# File Watching & Automatic Ingestion

Memoir supports **automatic file monitoring** for both **local folders** and **cloud storage** (Google Drive, OneDrive). When files are added, modified, or deleted, the system automatically triggers ingestion or cleanup.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    File Watching System                      │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────┐                 ┌──────────────────┐
│  Local Folders   │                 │  Cloud Folders   │
│   (Watchdog)     │                 │ (Drive/OneDrive) │
└──────────────────┘                 └──────────────────┘
        │                                       │
        └───────────────────┬───────────────────┘
                            │
                            ▼
                  ┌─────────────────┐
                  │  Event Queue    │
                  │  (Debouncing)   │
                  └─────────────────┘
                            │
                            ▼
                  ┌─────────────────┐
                  │  File Handling  │
                  │  Server :8080   │
                  └─────────────────┘
                            │
                            ▼
                  ┌─────────────────┐
                  │  Memoir API   │
                  │  Backend :8000  │
                  └─────────────────┘
```

## Components

### 1. **Local Folder Watching** (Filesystem Monitor)
- **Technology**: Python `watchdog` library
- **Monitors**: Local directories on your computer
- **Events**: File created, modified, deleted
- **Debouncing**: 2-second delay to avoid duplicate events

### 2. **Cloud Folder Watching** (Public Cloud Monitor)
- **Supports**: 
  - Google Drive (public folders)
  - OneDrive (public folders)
- **Polling**: Checks every 60 seconds for changes
- **Auto-download**: Files are downloaded to `file_handling/tmp/`

### 3. **Event Queue**
- **Purpose**: Buffers file events before processing
- **Workers**: 2 concurrent workers (configurable)
- **Max Queue**: 500 events (configurable)

### 4. **File Handling Server**
- **Port**: 8080
- **Purpose**: REST API for adding folders to watch
- **Integration**: Calls Memoir backend for ingestion

---

## How It Works

### Local Folder Monitoring

1. **Add a folder to watch** via API:
   ```bash
   curl -X POST http://localhost:8080/monitor/local \
     -H "Content-Type: application/json" \
     -d '{"path": "/path/to/documents", "recursive": true}'
   ```

2. **File events detected**:
   - Watchdog observes filesystem changes in real-time
   - Events are debounced (2s delay) to avoid duplicates
   - Hidden files and temp files are ignored (`.hidden`, `~$temp`)

3. **Auto-ingestion triggered**:
   - `Created/Modified` → Calls `POST /api/ingest` on backend
   - `Deleted` → Removes document from database & vector store

4. **Console output**:
   ```
   📁 FILE EVENT: CREATED -> research_paper.pdf
   ✅ Backend ingested research_paper.pdf: doc_id=47
   ```

---

### Cloud Folder Monitoring

#### Google Drive

1. **Share your folder publicly**:
   - Right-click folder → Share → Get link → "Anyone with the link can view"

2. **Add to monitoring**:
   ```bash
   curl -X POST http://localhost:8080/monitor/cloud \
     -H "Content-Type: application/json" \
     -d '{"url": "https://drive.google.com/drive/folders/YOUR_FOLDER_ID", "recursive": true}'
   ```

3. **Background polling**:
   - Checks Google Drive API every 60 seconds
   - Downloads new/modified files to `file_handling/tmp/google_drive/`
   - Triggers ingestion automatically

4. **Requirements**:
   - Set `GOOGLE_API_KEY` in `file_handling/.env`
   - Get API key from [Google Cloud Console](https://console.cloud.google.com/)

#### OneDrive

1. **Get shareable link**:
   - Right-click folder → Share → Get link

2. **Add to monitoring**:
   ```bash
   curl -X POST http://localhost:8080/monitor/cloud \
     -H "Content-Type: application/json" \
     -d '{"url": "https://1drv.ms/f/YOUR_LINK", "recursive": true}'
   ```

3. **Background polling**:
   - Checks OneDrive Graph API every 60 seconds
   - Downloads to `file_handling/tmp/onedrive/`

---

## Setup & Usage

### Start the File Handling Server

```bash
# From project root
python file_handling/run_server.py --port 8080
```

Or with custom settings:
```bash
python file_handling/run_server.py --host 0.0.0.0 --port 8080
```

### Configuration

Edit `file_handling/.env`:
```env
# Google Drive API
GOOGLE_API_KEY=your_api_key_here

# Ingestion settings
MAX_QUEUE_SIZE=500
PROCESSING_WORKERS=2
BACKEND_URL=http://localhost:8000

# Polling intervals
UPDATE_CHECK_INTERVAL=60  # seconds
```

---

## API Endpoints

### File Handling Server (`:8080`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/monitor/local` | Add local folder to watch |
| `POST` | `/monitor/cloud` | Add Google Drive/OneDrive folder |
| `GET` | `/monitor/status` | Get monitoring status & stats |
| `GET` | `/events` | List recent file events |
| `DELETE` | `/monitor/local/{folder_id}` | Stop monitoring local folder |

### Example: Monitor Local Folder

```bash
curl -X POST http://localhost:8080/monitor/local \
  -H "Content-Type: application/json" \
  -d '{
    "path": "C:/Users/User/Documents",
    "recursive": true
  }'
```

### Example: Monitor Google Drive

```bash
curl -X POST http://localhost:8080/monitor/cloud \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://drive.google.com/drive/folders/1abc...xyz",
    "recursive": true
  }'
```

### Example: Check Status

```bash
curl http://localhost:8080/monitor/status
```

Response:
```json
{
  "local_folders": 2,
  "cloud_folders": 1,
  "files_tracked": 45,
  "events_generated": 128,
  "queue_size": 0,
  "workers_running": 2
}
```

---

## Integration with Memoir Backend

When the File Handling Server detects file events, it automatically calls the Memoir backend:

### File Created/Modified
```
File Handling Server → POST /api/ingest → Memoir Backend
                        (with file path)
```
- Backend runs full ingestion pipeline
- Text extraction, chunking, embedding
- Stores in Postgres + Qdrant
- Rebuilds knowledge graphs

### File Deleted
```
File Handling Server → DELETE /api/files → Memoir Backend
                        (with file path)
```
- Backend removes document from database
- Deletes vectors from Qdrant
- Updates knowledge graphs

---

## Standalone File Watcher Service

For **direct integration** without the HTTP server, use the standalone service:

```bash
python file_handling/file_watcher.py --watch /path/to/folder --recursive
```

This mode:
- Monitors specified directories directly
- Calls ingestion pipeline in-process (no HTTP)
- Auto-rebuilds graphs after each file

Options:
```bash
--watch DIR [DIR ...]     Directories to watch (default: data/raw)
--recursive              Watch subdirectories (default: True)
--debounce SECONDS       Debounce delay (default: 2.0)
--no-auto-rebuild        Disable automatic graph rebuilding
```

---

## Event Flow Examples

### Example 1: Add a Text File Locally

```
1. User: Copy "report.txt" to watched folder
2. Watchdog: Detects file creation event
3. Event Queue: Debounces for 2 seconds
4. File Handling Server: Receives event
5. Console Output: "📁 FILE EVENT: CREATED -> report.txt"
6. Backend Call: POST /api/ingest {"directory": "/path/to/folder"}
7. Memoir: Ingests file (extract → chunk → embed → store)
8. Console Output: "✅ Backend ingested report.txt: doc_id=47"
9. Frontend: Automatically fetches updated document list
10. UI: "report.txt" appears in constellation graph
```

### Example 2: Update a File in Google Drive

```
1. User: Edits "notes.pdf" in Google Drive (web)
2. Cloud Monitor: Polls Drive API (every 60s)
3. Cloud Monitor: Detects file modification
4. Cloud Monitor: Downloads updated file to tmp/google_drive/
5. Event Queue: Receives "modified" event
6. File Handling Server: Triggers ingestion
7. Memoir: Re-ingests file (overwrites old version)
8. Graphs: Automatically rebuilt
9. UI: Updated content available immediately
```

### Example 3: Delete a Document

```
1. User: Deletes "old_doc.pdf" from watched folder
2. Watchdog: Detects deletion event
3. File Handling Server: "🗑️ FILE EVENT: DELETED -> old_doc.pdf"
4. Backend Call: Finds document by file_path
5. Memoir: Removes from Postgres + Qdrant
6. Console Output: "✅ Backend cleaned up old_doc.pdf"
7. UI: Document disappears from graph
```

---

## Troubleshooting

### Files Not Being Detected

1. **Check if server is running**:
   ```bash
   curl http://localhost:8080/monitor/status
   ```

2. **Check Memoir backend is reachable**:
   ```bash
   curl http://localhost:8000/api/health
   ```

3. **Check logs**:
   - File Handling Server: Console output shows file events
   - Memoir Backend: Look for ingestion logs

### Cloud Folders Not Syncing

1. **Verify API keys**:
   - Google Drive: Check `GOOGLE_API_KEY` in `.env`
   - OneDrive: Ensure folder is publicly accessible

2. **Check polling interval**:
   - Default is 60 seconds
   - Enable verbose logging to see poll attempts

### Files Ingested But Not Showing in UI

1. **Check database**:
   ```bash
   cd backend
   python -c "from app.db import postgres as pg; s = pg.get_session(); print(len(s.query(pg.Document).all())); s.close()"
   ```

2. **Check frontend API connection**:
   - Open browser console (F12)
   - Look for `[API] GET /api/documents` logs
   - Verify response contains documents

3. **Reload frontend**:
   - Refresh page (Ctrl+R)
   - Check if documents appear

---

## Performance Notes

- **Local monitoring**: Real-time, no delay (except 2s debounce)
- **Cloud polling**: 60-second intervals (configurable)
- **Max concurrent ingestions**: 2 workers (configurable)
- **Large files**: May take longer to process (PDFs, images with VLM)
- **Memory**: VLM captioning uses GPU VRAM (6GB recommended)

---

## Architecture Decisions

### Why Two Separate Servers?

1. **Separation of Concerns**:
   - File Handling (`:8080`): Monitoring & event management
   - Memoir (`:8000`): RAG pipeline & business logic

2. **Scalability**:
   - File server can run on different machine
   - Multiple file servers can feed one backend

3. **Flexibility**:
   - Can use standalone watcher service if HTTP not needed
   - Can swap monitoring implementations independently

### Why Debouncing?

- Rapid file edits generate many events
- Debouncing waits 2s to ensure file is stable
- Prevents duplicate ingestions
- Reduces backend load

### Why Polling for Cloud?

- Most cloud APIs don't support webhooks for public folders
- Polling every 60s is efficient and reliable
- Immediate webhooks would require authentication & setup

---

## Future Enhancements

- [ ] WebSocket support for real-time UI updates
- [ ] Webhook support for Google Drive/OneDrive (authenticated)
- [ ] File conflict resolution (multiple edits)
- [ ] Incremental ingestion (only changed chunks)
- [ ] Support for SharePoint and Dropbox
- [ ] File versioning and history tracking
- [ ] Selective sync (file type filters, size limits)

---

## Summary

The file watching system provides **zero-configuration automatic ingestion** for your knowledge base:

✅ **Add a local folder** → Files automatically ingested  
✅ **Share a Drive folder** → Changes automatically synced  
✅ **Delete a file** → Automatically removed from database  
✅ **Edit a document** → Automatically re-ingested  

No manual upload needed. Just point the watcher at your folders and let Memoir handle the rest.
