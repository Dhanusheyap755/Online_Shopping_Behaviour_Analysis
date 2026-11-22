"""
Probes Streamlit server startup and HTTP 200 health check.
"""
import subprocess
import time
import urllib.request
import os
import signal

def probe():
    cwd = r"C:\Users\abidh\.gemini\antigravity\scratch\Online_Shopping_Behaviour_Analysis"
    cmd = [
        "python", "-m", "streamlit", "run", "app.py",
        "--server.headless=true",
        "--server.port=8501",
        "--browser.serverAddress=localhost"
    ]
    print("Launching Streamlit server...")
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)

    try:
        url = "http://localhost:8501"
        print(f"Probing {url}...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            content = response.read(500).decode('utf-8', errors='ignore')
            print(f"HTTP Status: {status}")
            print(f"Content preview: {content[:150]}...")
            assert status == 200, f"Expected 200, got {status}"
            print("Streamlit web server probe SUCCESSFUL!")
    finally:
        print("Terminating server process...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        print("Server shutdown cleanly.")

if __name__ == "__main__":
    probe()
