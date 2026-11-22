"""
Probes local HTTP server serving docs/index.html and github-pages/index.html.
"""
import http.server
import socketserver
import threading
import urllib.request
import os
import time

PORT = 8088
base_dir = r"C:\Users\abidh\.gemini\antigravity\scratch\Online_Shopping_Behaviour_Analysis"

os.chdir(base_dir)

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def run_server():
    with socketserver.TCPServer(("", PORT), QuietHandler) as httpd:
        httpd.serve_forever()

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(1)

print(f"HTTP server listening on port {PORT}...")

urls_to_test = [
    f"http://localhost:{PORT}/index.html",
    f"http://localhost:{PORT}/github-pages/index.html",
    f"http://localhost:{PORT}/docs/index.html",
    f"http://localhost:{PORT}/docs/style.css",
    f"http://localhost:{PORT}/docs/script.js",
    f"http://localhost:{PORT}/docs/assets/data/default_dataset.js"
]

all_passed = True
for url in urls_to_test:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
            content = resp.read()
            size = len(content)
            
            # Verify that docs/index.html contains dashboard DOM elements, not README markdown
            if "docs/index.html" in url:
                text = content.decode('utf-8', errors='ignore')
                assert "<title>Online Shopping Behaviour & Purchase Trend Analysis</title>" in text
                assert "app-container" in text
                assert "Executive Overview" in text
                assert "# ONLINE SHOPPING" not in text  # Ensure not raw README markdown!
                print(f"VERIFIED {url} -> Content is the REAL INTERACTIVE DASHBOARD (not README markdown)!")

            print(f"PROBE {url} -> Status: {status}, Size: {size:,} bytes [OK]")
    except Exception as e:
        print(f"PROBE FAILED {url} -> {e}")
        all_passed = False

if all_passed:
    print("\n🎉 ALL GITHUB PAGES ASSETS AND ENDPOINTS VERIFIED WITH HTTP 200!")
else:
    raise RuntimeError("One or more asset probes failed!")
