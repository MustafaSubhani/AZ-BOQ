"""Decode the newest CDP Page.captureScreenshot response into cache/shots/<name>.jpg."""
import base64
import json
import sys
from pathlib import Path

logs = Path.home() / ".cursor" / "browser-logs"
latest = max(logs.glob("cdp-response-Page.captureScreenshot-*.json"), key=lambda p: p.stat().st_mtime)
data = json.loads(latest.read_text(encoding="utf-8"))
b64 = data.get("data") or data.get("result", {}).get("data")
out = Path(__file__).resolve().parents[2] / "cache" / "shots" / f"{sys.argv[1] if len(sys.argv) > 1 else 'shot'}.jpg"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(base64.b64decode(b64))
print(out)
