# File Handling Module

Unified file monitoring system for local filesystem and cloud folders (Google Drive, OneDrive).

## Features

- 📁 Monitor local folders recursively
- ☁️ Monitor public Google Drive and OneDrive folders
- 💾 Downloads all files to `/tmp` directory
- 🔔 Event notifications for create/modify/delete operations
- 🖨️ Prints "hello talel" on file add/modify, "bye talel" on delete
- 🌐 FastAPI REST API for remote monitoring

## Installation

```bash
pip install -r file_handling/requirements.txt
```

## Quick Start

### Option 1: Run Server from file_handling folder

```bash
cd file_handling
python run_server.py
```

### Option 2: Run Server from project root

```bash
python file_handling/run_server.py
```

### Option 3: Custom Port/Host

```bash
python file_handling/run_server.py --host 0.0.0.0 --port 8080
```

### Option 3: Python Module

```python
from file_handling import FilesystemMonitor, PublicCloudMonitor, EventQueue

# Create event queue
queue = EventQueue()

def event_handler(event):
    print(f"Event: {event.event_type} - {event.file_path}")
    return True

queue.start_workers(event_handler, num_workers=2)

# Create filesystem monitor
fs_monitor = FilesystemMonitor(event_queue=queue)
fs_monitor.add_watch_path("C:/Users/User/Documents")
fs_monitor.start()

# Create cloud monitor
cloud_monitor = PublicCloudMonitor(
    event_queue=queue,
    google_api_key="YOUR_API_KEY",
    poll_interval=30
)
cloud_monitor.add_folder("https://drive.google.com/drive/folders/YOUR_FOLDER_ID?usp=sharing")
cloud_monitor.start()

# Keep running
import time
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    fs_monitor.stop()
    cloud_monitor.stop()
    queue.stop_workers()
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/
```

### Get Statistics
```bash
curl http://localhost:8000/stats
```

### List Tracked Files
```bash
curl http://localhost:8000/files
```

### Get Recent Events
```bash
curl http://localhost:8000/events?limit=50
```

### Add Local Folder
**Important:** Use forward slashes `/` or double backslashes `\\` in paths for JSON:
```bash
# Using forward slashes (recommended):
curl -X POST http://localhost:8000/folders/local \
  -H "Content-Type: application/json" \
  -d '{"path": "C:/Users/User/Documents", "recursive": true}'

# Using double backslashes:
curl -X POST http://localhost:8000/folders/local \
  -H "Content-Type: application/json" \
  -d '{"path": "C:\\Users\\User\\Documents", "recursive": true}'
```

### Add Cloud Folder (Google Drive)
```bash
curl -X POST http://localhost:8000/folders/cloud \
  -H "Content-Type: application/json" \
  -d '{"url": "https://drive.google.com/drive/folders/YOUR_ID?usp=sharing", "recursive": true}'
```

### Add Cloud Folder (OneDrive)
```bash
curl -X POST http://localhost:8000/folders/cloud \
  -H "Content-Type: application/json" \
  -d '{"url": "https://1drv.ms/f/s!YOUR_SHARE_ID", "recursive": true}'
```

### List Downloaded Files in /tmp
```bash
curl http://localhost:8000/tmp
```

### Clear /tmp Directory
```bash
curl -X DELETE http://localhost:8000/tmp
```

## Environment Variables

Create a `.env` file:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

## File Structure

```
file_handling/
├── __init__.py               # Module exports
├── config.py                 # Configuration settings
├── storage_schemas.py        # Data models (FileEvent, EventType, etc.)
├── event_queue.py            # Thread-safe event queue
├── shareable_link_parser.py  # Google Drive & OneDrive URL parser
├── public_gdrive_access.py   # Google Drive public folder access
├── public_onedrive_access.py # OneDrive public folder access
├── filesystem_watcher.py     # Local filesystem monitoring
├── public_cloud_monitor.py   # Cloud folder monitoring
├── server.py                 # FastAPI server & endpoints
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## Events

The monitor emits `FileEvent` objects with:

- `event_type`: CREATED, MODIFIED, or DELETED
- `source`: LOCAL, GOOGLE_DRIVE, or ONEDRIVE
- `file_path`: Original file path (local or cloud URL)
- `local_path`: Path to downloaded file in `/tmp`
- `metadata`: Additional info (name, size, type, etc.)

## Tmp Directory

All monitored files are downloaded to `<project_root>/tmp/`:

```
tmp/
├── local/          # Local filesystem files
├── google_drive/   # Google Drive downloads
└── onedrive/       # OneDrive downloads
```

## Console Output

When files are added/modified:
```
hello talel
```

When files are deleted:
```
bye talel
```

## Example: Monitor Everything

```python
from file_handling import FilesystemMonitor, PublicCloudMonitor, EventQueue
import time

# Create event queue and processor
queue = EventQueue()

def handle_event(event):
    print(f"Event: {event.event_type} - {event.file_path}")
    return True

queue.start_workers(handle_event, num_workers=2)

# Create filesystem monitor
fs_monitor = FilesystemMonitor(event_queue=queue)
fs_monitor.add_watch_path("C:/Users/User/Documents")
fs_monitor.add_watch_path("C:/Users/User/Downloads")
fs_monitor.start()

# Create cloud monitor
cloud_monitor = PublicCloudMonitor(event_queue=queue, poll_interval=30)
cloud_monitor.add_folder("https://drive.google.com/...")
cloud_monitor.start()

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    fs_monitor.stop()
    cloud_monitor.stop()
    queue.stop_workers()
```

## API Integration Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Add folder
response = requests.post(
    f"{BASE_URL}/folders/local",
    json={"path": "C:/MyFolder", "recursive": True}
)
print(response.json())

# Get stats
stats = requests.get(f"{BASE_URL}/stats").json()
print(f"Tracking {stats['files_tracked']} files")

# Get recent events
events = requests.get(f"{BASE_URL}/events?limit=10").json()
for event in events:
    print(f"{event['event_type']}: {event['metadata']['relative_path']}")
```

## Requirements

- Python 3.10+
- `watchdog` - Local filesystem monitoring
- `fastapi` + `uvicorn` - REST API server
- `google-api-python-client` - Google Drive access
- `requests` - HTTP requests for OneDrive

See [requirements.txt](requirements.txt) for full list.
