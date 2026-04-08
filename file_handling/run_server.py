#!/usr/bin/env python3
"""
Run the File Handling Server
Usage: python file_handling/run_server.py [--port PORT] [--host HOST]
        or cd file_handling && python run_server.py
"""
import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path if running from file_handling folder
if __name__ == "__main__":
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))


def main():
    parser = argparse.ArgumentParser(description="File Handling Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to (default: 8080)")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload")
    parser.add_argument("--backend", default=None, help="Backend API URL (default: http://localhost:8000)")
    
    args = parser.parse_args()
    
    # Set backend URL if provided
    if args.backend:
        os.environ["BACKEND_URL"] = args.backend
    
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    
    print("=" * 60)
    print("  File Handling Server")
    print("=" * 60)
    print()
    print(f"Starting server on http://{args.host}:{args.port}")
    print(f"Backend API: {backend_url}")
    print()
    print("API Endpoints:")
    print("  GET  /              - Health check")
    print("  GET  /stats         - Monitor statistics")
    print("  GET  /files         - List tracked files")
    print("  GET  /events        - Recent file events")
    print("  POST /folders/local - Add local folder")
    print("  POST /folders/cloud - Add cloud folder (Google Drive/OneDrive)")
    print("  GET  /folders       - List all folders")
    print("  GET  /tmp           - List tmp files")
    print("  DELETE /tmp         - Clear tmp directory")
    print()
    print("Example - Add Local Folder (use forward slashes):")
    print(f'  curl -X POST http://localhost:{args.port}/folders/local \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"path": "C:/Users/User/Documents", "recursive": true}\'')
    print()
    print("Example - Add Google Drive Folder:")
    print(f'  curl -X POST http://localhost:{args.port}/folders/cloud \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"url": "https://drive.google.com/drive/folders/YOUR_ID?usp=sharing", "recursive": true}\'')
    print()
    print("NOTE: File events will be sent to backend for ingestion/deletion")
    print(f"      Make sure backend is running at {backend_url}")
    print()
    print("Press Ctrl+C to stop")
    print("-" * 60)
    print()
    
    import uvicorn
    uvicorn.run(
        "file_handling.api.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
