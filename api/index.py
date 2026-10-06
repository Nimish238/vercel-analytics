import json
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()


# Fallback: guarantees the header even when no Origin header is sent
@app.middleware("http")
async def force_cors(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# Added last, so it is outermost: handles OPTIONS preflight and Origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Access-Control-Allow-Origin"],
)


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
    return JSONResponse({"regions": result})