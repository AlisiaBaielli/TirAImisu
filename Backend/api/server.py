from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

from Backend.storage.events import get_events, set_events

app = FastAPI(title="Prosus Calendar API", version="1.0.0")

allowed_origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

cors_extra = os.getenv("CORS_EXTRA_ORIGINS")
if cors_extra:
    allowed_origins.extend([o.strip() for o in cors_extra.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/calendar/{calendar_id}/events")
def get_calendar_events(calendar_id: str) -> dict:
    """
    Return cached events for the given calendar_id.
    If cache is empty, attempt a best-effort live fetch (if env is set) and store the result.
    """
    try:
        events = get_events(calendar_id)
        if events:
            return {"events": events}
        # Best-effort live fetch if cache empty
        try:
            from Backend.calendar.cal_api import list_events as live_list_events

            live = live_list_events(calendar_id)
            if isinstance(live, list):
                set_events(calendar_id, live)
                return {"events": live}
        except Exception:
            # Ignore live fetch issues; return empty cache
            pass
        return {"events": []}
    except Exception as exc:
        # Surface a clear error to the client
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/calendar/{calendar_id}/events/refresh")
def refresh_calendar_events(calendar_id: str) -> dict:
    """
    Force refresh events from the external Calendar API and persist to cache.
    Requires CAL_API_BASE_URL, CAL_API_TOKEN, TIMEZONE to be configured.
    """
    try:
        from Backend.calendar.cal_api import list_events as live_list_events

        live = live_list_events(calendar_id)
        if not isinstance(live, list):
            raise HTTPException(status_code=502, detail="Invalid events format from upstream")
        set_events(calendar_id, live)
        return {"events": live}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# Optional: allow `python -m Backend.api.server` to run the dev server directly
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "Backend.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


