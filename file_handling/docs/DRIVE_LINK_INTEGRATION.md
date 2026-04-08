# Cloud Drive Integration Guide

## ✅ Overview

The ingestion pipeline now supports **Google Drive** and **OneDrive** shareable links! You can directly ingest documents from cloud storage without manually downloading them.

## 🔗 Supported Links

### Google Drive
```
✅ Folder: https://drive.google.com/drive/folders/FOLDER_ID?usp=sharing
✅ Folder: https://drive.google.com/drive/folders/FOLDER_ID
✅ File: https://drive.google.com/file/d/FILE_ID/view
✅ File: https://drive.google.com/open?id=FILE_ID
```

### OneDrive
```
✅ Folder: https://1drv.ms/f/s!SHARED_ID
✅ Folder: https://onedrive.live.com/redir?resid=RESOURCE_ID
✅ SharePoint: https://company.sharepoint.com/:f:/g/personal/user/FOLDER_ID
```

## 🚀 Setup

### 1. Google Drive API Key (Required for Google Drive)

Get a free API key from [Google Cloud Console](https://console.cloud.google.com/):

1. Create or select a project
2. Enable **Google Drive API**
3. Go to **Credentials** → **Create Credentials** → **API Key**
4. Copy the API key

#### Set Environment Variable

**Linux/Mac:**
```bash
export GOOGLE_API_KEY="YOUR_API_KEY_HERE"
```

**Windows (PowerShell):**
```powershell
$env:GOOGLE_API_KEY="YOUR_API_KEY_HERE"
```

**Or add to `.env` file:**
```bash
GOOGLE_API_KEY=YOUR_API_KEY_HERE
```

### 2. Install Dependencies

```bash
pip install google-api-python-client requests
```

## 📖 Usage

### Via API (cURL)

```bash
# Google Drive folder
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "https://drive.google.com/drive/folders/1abc...xyz?usp=sharing",
    "rebuild_graphs": true
  }'

# OneDrive folder
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "https://1drv.ms/f/s!AjK...",
    "rebuild_graphs": true
  }'
```

### Via UI

1. **Click the green ➕ button** in the bottom-right corner
2. **Paste your drive link** in the input field:
   - Google Drive: `https://drive.google.com/drive/folders/...`
   - OneDrive: `https://1drv.ms/f/s!...`
3. **Check "Rebuild graphs"** (recommended)
4. **Click "🚀 Start Ingestion"**
5. **Watch the progress** - files will be downloaded and processed

## 🔍 How It Works

```
User provides drive link
    ↓
Backend detects it's a drive link (not a local path)
    ↓
Parse link to extract folder/file ID
    ↓
Download files to temporary directory:
    - Google Drive: file_handling/tmp/google_drive/
    - OneDrive: file_handling/tmp/onedrive/
    ↓
Run standard ingestion pipeline on downloaded files
    ↓
Files are processed, embedded, and indexed
    ↓
Knowledge graph is rebuilt
    ↓
Files appear in UI!
```

## 📋 Requirements

### Folder/File Sharing

**Google Drive:**
- Folder/file must be set to **"Anyone with the link can view"**
- Or set to public/discoverable

**OneDrive:**
- Folder/file must have **"People with the link"** access
- Or be publicly shared

### Supported File Types

Same as local ingestion:
- **Text**: `.txt`, `.md`, `.csv`, `.json`, `.xml`, etc.
- **Documents**: `.pdf`, `.doc`, `.docx`
- **Images**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`
- **Audio**: `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`

## 🧪 Testing

### Test with Sample Google Drive Folder

```bash
# Create a test folder in Google Drive
# Add some PDFs, text files, images
# Share it: Right-click → Share → Get link → Anyone with link can view
# Copy the link

# Test via API
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "YOUR_GOOGLE_DRIVE_LINK_HERE",
    "rebuild_graphs": true
  }'

# Check logs
tail -f backend/logs/ingestion.log
```

## 🔧 Troubleshooting

### "Google Drive service not initialized"

**Problem:** No API key set
**Solution:** 
```bash
export GOOGLE_API_KEY="your-key-here"
# Or add to .env file
```

### "Folder not found or not public"

**Problem:** Folder is not shared publicly
**Solution:** 
1. Right-click folder in Google Drive
2. Click "Share"
3. Change to "Anyone with the link can view"
4. Copy the link and try again

### "Failed to download files from drive link"

**Problem:** Rate limiting or network issues
**Solution:**
- Wait a few minutes and retry
- Check internet connection
- Verify the link is accessible in browser

### "Access denied. Item may not be publicly shared"

**Problem:** OneDrive folder/file is private
**Solution:**
1. Right-click item in OneDrive
2. Click "Share"
3. Set to "Anyone with the link"
4. Copy link and try again

## 📊 Console Logs

Watch for these logs to track progress:

```
[workflow] Detected drive link: https://drive.google.com/...
[workflow] Downloading files from Google Drive folder...
[workflow] Downloaded: research_paper.pdf
[workflow] Downloaded: notes.txt
[workflow] Downloaded 5 files from Google Drive to /tmp/google_drive
[workflow] Found 5 files in /tmp/google_drive
[workflow] Ingested research_paper.pdf → doc_id=42, 15 chunks
[workflow] Pipeline complete: {ingested: 5, failed: 0, graph_built: true}
```

## 🎯 Use Cases

### Research Papers from Shared Folder
```
1. Collaborators add papers to shared Google Drive folder
2. Paste folder link into ingestion UI
3. All papers are automatically processed and searchable
```

### Team Documents from OneDrive
```
1. Team shares OneDrive folder with project docs
2. Use API or UI to ingest the folder
3. Documents indexed for AI-powered search and chat
```

### Regular Sync (Future Enhancement)
```
# Coming soon: Automatic monitoring of drive links
# Files will be automatically re-ingested when changed
```

## 🔐 Privacy & Security

- **Only publicly shared links** are supported (no authentication)
- Files are downloaded to **temporary local directory** for processing
- **Original files remain in cloud** - we only read them
- Downloaded files can be deleted after ingestion (they're in vector DB)
- No access to private files or folders

## 💡 Pro Tips

1. **Organize by folders**: Share separate folders for different topics/projects
2. **Use meaningful names**: File names appear in search results and graph
3. **Update regularly**: Re-run ingestion periodically to pick up new files
4. **Watch file limits**: Google Drive API has rate limits (monitor logs)
5. **Clear cache**: Delete `file_handling/tmp/` to free up space

## 📚 Examples

### Example 1: Research Library
```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "https://drive.google.com/drive/folders/1abc-research-papers",
    "rebuild_graphs": true
  }'
```

### Example 2: Company Knowledge Base
```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "https://1drv.ms/f/s!company-docs-2024",
    "rebuild_graphs": true
  }'
```

### Example 3: Mixed Sources
```bash
# Ingest local files first
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"directory": "C:/Users/User/Documents", "rebuild_graphs": false}'

# Then ingest from Google Drive
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "https://drive.google.com/drive/folders/...",
    "rebuild_graphs": true
  }'
```

---

**Ready to use!** The `/api/ingest` endpoint now seamlessly handles both local paths and cloud drive links. Just paste your link and let the system do the rest! 🎉
