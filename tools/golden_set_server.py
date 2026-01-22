"""
Golden Set Annotation Server
Run: python tools/golden_set_server.py
Opens browser at http://localhost:8765
"""

import http.server
import socketserver
import json
import os
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT = 8765
BASE_DIR = Path(__file__).parent.parent
IMAGES_DIR = BASE_DIR / "temp_images"


class GoldenSetHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        
        # Ignore favicon requests
        if parsed.path == "/favicon.ico":
            self.send_response(204)  # No Content
            self.end_headers()
            return
        
        # API: List all images
        if parsed.path == "/api/images":
            self.send_json_response(self.get_image_list())
            return
        
        # Serve the UI at root
        if parsed.path == "/" or parsed.path == "":
            self.path = "/tools/golden_set.html"
        
        return super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def get_image_list(self):
        """Get all jpg/png images from temp_images folder"""
        if not IMAGES_DIR.exists():
            return {"images": [], "error": "temp_images directory not found"}
        
        extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        images = []
        
        for f in sorted(IMAGES_DIR.iterdir()):
            if f.suffix.lower() in extensions:
                images.append({
                    "filename": f.name,
                    "path": f"temp_images/{f.name}"
                })
                # Limit to 50 images for golden set creation
                if len(images) >= 50:
                    break
        
        return {"images": images, "total": len(images), "limited": True}

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        # Suppress default logging, show only important messages
        # Handle both string and HTTPStatus args safely
        if args and isinstance(args[0], str):
            if "/api/" in args[0] or "GET / " in args[0]:
                print(f"[Server] {args[0]}")


def main():
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           Golden Set Annotation Tool                         ║
╠══════════════════════════════════════════════════════════════╣
║  Server running at: http://localhost:{PORT}                    ║
║  Images folder: {IMAGES_DIR}
║  Press Ctrl+C to stop                                        ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    with socketserver.TCPServer(("", PORT), GoldenSetHandler) as httpd:
        # Open browser automatically
        webbrowser.open(f"http://localhost:{PORT}")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[Server] Shutting down...")
            httpd.shutdown()


if __name__ == "__main__":
    main()
