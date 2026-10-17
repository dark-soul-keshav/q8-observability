import json
import time
import uuid
from collections import deque
from threading import Lock

from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse

app = FastAPI()

EMAIL = "24f3002937@ds.study.iitm.ac.in"
START_TIME = time.monotonic()

request_count = 0
counter_lock = Lock()
logs = deque(maxlen=1000)
logs_lock = Lock()


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    global request_count

    request_id = str(uuid.uuid4())
    started = time.time()

    with counter_lock:
        request_count += 1

    try:
        response = await call_next(request)
        level = "INFO" if response.status_code < 500 else "ERROR"
        return response
    except Exception:
        level = "ERROR"
        raise
    finally:
        entry = {
            "level": level,
            "ts": started,
            "path": request.url.path,
            "request_id": request_id,
        }
        with logs_lock:
            logs.append(entry)


@app.get("/work")
def work(n: int = Query(..., ge=0, le=1000000)):
    # Perform a bounded amount of work.
    total = sum(range(n + 1))
    return {"email": EMAIL, "done": n}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    with counter_lock:
        count = request_count

    return (
        "# HELP http_requests_total Total HTTP requests received\n"
        "# TYPE http_requests_total counter\n"
        f"http_requests_total {count}\n"
    )


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "uptime_s": max(0.0, time.monotonic() - START_TIME),
    }


@app.get("/logs/tail")
def logs_tail(limit: int = Query(100, ge=0, le=1000)):
    with logs_lock:
        entries = list(logs)[-limit:] if limit else []
    return entries
