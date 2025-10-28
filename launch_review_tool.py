#!/usr/bin/env python3
"""
Launch the interactive review tool in a web browser
Serves review_tool.html and yellow_review_queue.json
"""

import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8888

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow fetch() to work
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def main():
    # Verify files exist
    if not Path('review_tool.html').exists():
        print("❌ Error: review_tool.html not found")
        return
    
    if not Path('yellow_review_queue.json').exists():
        print("❌ Error: yellow_review_queue.json not found")
        return
    
    print("="*80)
    print("🚀 LAUNCHING INTERACTIVE REVIEW TOOL")
    print("="*80)
    print(f"\n📊 Review Queue: {len(open('yellow_review_queue.json').read())} bytes loaded")
    print(f"\n🌐 Server starting on: http://localhost:{PORT}")
    print(f"\n✨ Opening browser automatically...")
    print(f"\n⚠️  Press Ctrl+C to stop the server when done\n")
    print("="*80 + "\n")
    
    # Change to current directory
    os.chdir(Path(__file__).parent)
    
    # Create server
    handler = MyHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        # Open browser
        webbrowser.open(f'http://localhost:{PORT}/review_tool.html')
        
        print(f"✅ Server running! Review tool should open in your browser.\n")
        print(f"💡 If it doesn't open automatically, visit:")
        print(f"   http://localhost:{PORT}/review_tool.html\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n⏹️  Server stopped. Review saved to manual_review_decisions.json\n")

if __name__ == '__main__':
    main()
