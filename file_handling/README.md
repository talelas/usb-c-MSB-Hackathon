# File Handling Server

Standalone server that monitors local folders and cloud storage (Google Drive, OneDrive) for file changes, then automatically triggers ingestion in the Memoir backend.

→ **See the [root README](../README.md) for the full project overview.**

---

## Structure

```
file_handling/
├── api/
│   └── server.py              # FastAPI server (port 8080)
├── core/
│   ├── event_queue.py         # Debounced event queue + worker pool
│   ├── storage_schemas.py     # Pydantic schemas
│   └── config.py              # Env-based config
├── watchers/
│   ├── filesystem_watcher.py  # Watchdog-based local folder monitor
│   └── public_cloud_monitor.py# Google Drive + OneDrive polling
├── cloud/
│   ├── public_gdrive_access.py# Google Drive API client
│   ├── public_onedrive_access.py # OneDrive Graph API client
│   └── shareable_link_parser.py # Parse Drive/OneDrive URLs
├── docs/
│   ├── FILE_WATCHING.md       # Full file watching guide
│   └── DRIVE_LINK_INTEGRATION.md  # Drive link ingestion guide
├── tmp/                       # git-ignored — temporary cloud downloads
├── run_server.py              # Entry-point (CLI flags)
├── requirements.txt
├── .env.example
└── .env                       # git-ignored
```

---

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # set GOOGLE_API_KEY, BACKEND_URL, etc.
python run_server.py --port 8080
```

---

## API Endpoints (port 8080)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/monitor/local` | Add local folder to watch |
| `POST` | `/monitor/cloud` | Add Google Drive / OneDrive folder |
| `GET`  | `/monitor/status` | Monitoring status & stats |
| `GET`  | `/events` | Recent file events |
| `DELETE` | `/monitor/local/{folder_id}` | Stop monitoring a folder |

---

## Examples

```bash
# Watch a local folder
curl -X POST http://localhost:8080/monitor/local \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/documents", "recursive": true}'

# Watch a Google Drive folder
curl -X POST http://localhost:8080/monitor/cloud \
  -H "Content-Type: application/json" \
  -d '{"url": "https://drive.google.com/drive/folders/YOUR_ID", "recursive": true}'
```

---

## Further Reading

- [File Watching Guide](docs/FILE_WATCHING.md) — architecture, event flow, troubleshooting
- [Drive Link Integration](docs/DRIVE_LINK_INTEGRATION.md) — Google Drive + OneDrive setup
