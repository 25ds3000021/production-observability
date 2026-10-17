
import time
import uuid
import logging
from datetime import datetime, timezone
from collections import deque

from fastapi import FastAPI, Request, Query
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()

EMAIL = "25ds3000021@ds.study.iitm.ac.in"

start_time = time.monotonic()

request_counter = Counter(
    "http_requests_total",
    "Total number of HTTP requests"
)

recent_logs = deque(maxlen=1000)

logging.basicConfig(level=logging.INFO)


@app.middleware("http")
async def track_requests(request: Request, call_next):

    request_counter.inc()

    request_id = str(uuid.uuid4())

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        raise
    finally:
        log_entry = {
            "level": "INFO" if status_code < 500 else "ERROR",
            "ts": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path,
            "request_id": request_id,
            "method": request.method,
            "status_code": status_code
        }

        recent_logs.append(log_entry)

        logging.info(
            __import__("json").dumps(log_entry)
        )

    response.headers["X-Request-ID"] = request_id

    return response


@app.get("/work")
def do_work(n: int = Query(default=1, ge=0, le=10000)):

    result = 0

    for i in range(n):
        result += 1

    return {
        "email": EMAIL,
        "done": result
    }


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/healthz")
def health_check():
    return {
        "status": "ok",
        "uptime_s": float(time.monotonic() - start_time)
    }


@app.get("/logs/tail")
def get_logs(limit: int = Query(default=10, ge=0, le=1000)):
    if limit == 0:
        return []

    return list(recent_logs)[-limit:]
