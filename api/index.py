from http.server import BaseHTTPRequestHandler
import json
import os


def load_data():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (
        os.path.join(here, "..", "q-vercel-latency.json"),
        os.path.join(here, "q-vercel-latency.json"),
        os.path.join(os.getcwd(), "q-vercel-latency.json"),
    ):
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    raise FileNotFoundError("q-vercel-latency.json not found")


def percentile(values, p):
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def analyze(body):
    regions = body.get("regions", [])
    threshold = body.get("threshold_ms", 180)
    data = load_data()
    result = {}
    for r in regions:
        rows = [d for d in data if d["region"] == r]
        if not rows:
            continue
        lat = [d["latency_ms"] for d in rows]
        up = [d["uptime_pct"] for d in rows]
        result[r] = {
            "avg_latency": sum(lat) / len(lat),
            "p95_latency": percentile(lat, 95),
            "avg_uptime": sum(up) / len(up),
            "breaches": sum(1 for x in lat if x > threshold),
        }
    return result


class handler(BaseHTTPRequestHandler):
    def _send(self, status, payload=None):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        if payload is not None:
            out = json.dumps(payload).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        else:
            self.end_headers()

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        self._send(200, {"message": "Send a POST with {regions, threshold_ms}"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            body = json.loads(raw or b"{}")
            self._send(200, analyze(body))
        except Exception as e:
            self._send(500, {"error": str(e)})