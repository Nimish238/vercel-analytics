import json
import os
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "*",
}


@app.middleware("http")
async def add_cors(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(status_code=204, headers=CORS_HEADERS)
    try:
        response = await call_next(request)
    except Exception as e:
        response = JSONResponse({"error": str(e)}, status_code=500)
    for k, v in CORS_HEADERS.items():
        response.headers[k] = v
    return response


def load_data():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "q-vercel-latency.json"),
        os.path.join(here, "q-vercel-latency.json"),
        os.path.join(os.getcwd(), "q-vercel-latency.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    raise FileNotFoundError("q-vercel-latency.json not found in: " + ", ".join(candidates))


def percentile(values, p):
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


@app.post("/")
@app.post("/api")
@app.post("/api/index")
async def analyze(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
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
    return JSONResponse(result)