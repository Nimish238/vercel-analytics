from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import math
from pathlib import Path

# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI()

# --------------------------------------------------
# CORS configuration
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Load telemetry data
# --------------------------------------------------

DATA_FILE = Path(__file__).parent.parent / "q-vercel-latency.json"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    telemetry = json.load(f)

# --------------------------------------------------
# Request model
# --------------------------------------------------

class AnalyticsRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# --------------------------------------------------
# Percentile calculation
# --------------------------------------------------

def percentile(values, percentile_value):
    values = sorted(values)

    if not values:
        return 0

    position = (len(values) - 1) * percentile_value

    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return values[lower]

    return (
        values[lower]
        + (values[upper] - values[lower])
        * (position - lower)
    )

# --------------------------------------------------
# POST analytics endpoint
# --------------------------------------------------

@app.post("/")
def analytics(request: AnalyticsRequest):

    result = []

    for region in request.regions:

        records = [
            row
            for row in telemetry
            if row["region"] == region
        ]

        if not records:
            continue

        latencies = [
            row["latency_ms"]
            for row in records
        ]

        uptimes = [
            row["uptime_pct"]
            for row in records
        ]

        avg_latency = (
            sum(latencies) / len(latencies)
        )

        p95_latency = percentile(
            latencies,
            0.95
        )

        avg_uptime = (
            sum(uptimes) / len(uptimes)
        )

        breaches = sum(
            latency > request.threshold_ms
            for latency in latencies
        )

        result.append({
            "region": region,
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        })

    return result