from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

from Backend.storage.events import get_events, set_events
from Backend.medications.repository import get_current_medications, add_medication, get_medication_events
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta, date
from Backend.calendar.cal_tools import create_recurring_events
from fastapi import status

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

@app.get("/api/medications")
def list_medications() -> dict:
    """
    Return the current medications, serialized from the Medication class.
    """
    meds = [m.to_dict() for m in get_current_medications()]
    return {"medications": meds}

class MedicationCreate(BaseModel):
    name: str = Field(..., min_length=1)
    time: int = Field(..., ge=0, le=23)
    color: str = Field("med-blue")
    hour_interval: int = Field(24, ge=1)
    description: Optional[str] = None
    start_date: Optional[str] = None  # "YYYY-MM-DD"
    end_date: Optional[str] = None    # "YYYY-MM-DD"
    occurrences: Optional[int] = Field(None, ge=1)

@app.post("/api/medications")
def create_medication(payload: MedicationCreate) -> dict:
    """
    Append a new medication to the CSV store and return the created item.
    """
    med = add_medication(
        name=payload.name.strip(),
        time=payload.time,
        color=payload.color.strip(),
        hour_interval=payload.hour_interval,
        description=payload.description.strip() if payload.description else None,
        start_date=payload.start_date,
    )

    # Best-effort: create recurring calendar events
    try:
        calendar_id = os.getenv("CALENDAR_ID") or os.getenv("DEFAULT_CALENDAR_ID")
        if calendar_id:
            # Determine start datetime
            if payload.start_date:
                start_date_obj = datetime.strptime(payload.start_date, "%Y-%m-%d").date()
            else:
                start_date_obj = date.today()
            start_dt = datetime(
                year=start_date_obj.year,
                month=start_date_obj.month,
                day=start_date_obj.day,
                hour=med.time,
                minute=0,
            )
            end_dt = start_dt + timedelta(minutes=10)

            # Determine occurrences
            occ = payload.occurrences
            if not occ and payload.end_date:
                try:
                    end_date_obj = datetime.strptime(payload.end_date, "%Y-%m-%d").date()
                    total_hours = (datetime.combine(end_date_obj, datetime.min.time()) - datetime.combine(start_date_obj, datetime.min.time())).days * 24
                    occ = max(1, (total_hours // med.hour_interval) + 1)
                except Exception:
                    occ = None
            if not occ:
                occ = 7  # default one week of occurrences

            create_recurring_events(
                calendar_id=calendar_id,
                title=med.name,
                start_dt=start_dt,
                end_dt=end_dt,
                occurrences=occ,
                hour_interval=med.hour_interval,
                description=med.description,
                location=None,
            )
    except Exception:
        # Do not fail the request if calendar creation fails
        pass
    return {"medication": med.to_dict()}

@app.get("/api/medications/events")
def list_medication_events() -> dict:
    """
    Return medication-derived events generated from personal_medication.json
    (expanded with start_date and quantity_left).
    """
    events = get_medication_events()
    return {"events": events}

@app.get("/api/events-calendar/events")
def get_events_calendar_events() -> dict:
    """
    Return cached events for the EVENTS_CALENDAR_ID specified in the backend environment.
    Falls back to best-effort live fetch when cache is empty.
    """
    calendar_id = os.getenv("EVENTS_CALENDAR_ID")
    if not calendar_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="EVENTS_CALENDAR_ID env var not set")
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
            pass
        return {"events": []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/events-calendar/events/refresh")
def refresh_events_calendar_events() -> dict:
    """
    Force refresh for EVENTS_CALENDAR_ID and persist to cache.
    """
    calendar_id = os.getenv("EVENTS_CALENDAR_ID")
    if not calendar_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="EVENTS_CALENDAR_ID env var not set")
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


