import sys, urllib.error, urllib.request

url = "http://localhost:8000/health"
try:
    with urllib.request.urlopen(url, timeout=10) as resp:
        sys.exit(0 if resp.status < 400 else 1)
except Exception:
    sys.exit(1)
