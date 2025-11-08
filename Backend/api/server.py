from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Any, Dict, List
from pydantic import BaseModel
import json
import os

from Backend.storage.events import get_events, set_events
from Backend.medications.repository import get_current_medications, add_medication, get_medication_events
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta, date
from Backend.calendar.cal_tools import create_recurring_events
from fastapi import status

app = FastAPI(title="PillPal API", version="1.0.0")

# Allow local dev (add 5173 for Vite)
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
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

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(name: str) -> Any:
    p = DATA_DIR / name
    if not p.exists():
        raise HTTPException(status_code=500, detail=f"Missing data file: {name}")
    try:
        return json.loads(p.read_text())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in {name}: {exc}")


def _hash_color(name: str) -> str:
    colors = ["med-blue", "med-green", "med-orange", "med-purple", "med-pink", "med-yellow"]
    h = 0
    for ch in name:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return colors[h % len(colors)]


def _format_frequency(schedule: Dict[str, Any]) -> str:
    t = (schedule or {}).get("type")
    if t == "daily":
        times = schedule.get("times", [])
        return f"daily at {', '.join(times)}" if times else "daily"
    if t == "weekly":
        day = schedule.get("day")
        time = schedule.get("time")
        if day and time:
            return f"weekly on {day} at {time}"
        if day:
            return f"weekly on {day}"
        return "weekly"
    if t == "as_needed":
        m = schedule.get("max_per_day")
        return f"as needed (max {m}/day)" if m else "as needed"
    return "unspecified"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# -------- Auth --------
class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    users = _load_json("personal_data.json")
    user = next(
        (
            u
            for u in users
            if u.get("username") == payload.username and u.get("password") == payload.password
        ),
        None,
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Remove sensitive fields you do not want to expose (keep credit card only if required)
    sanitized = {k: v for k, v in user.items() if k not in ["password"]}
    return {
        "user_id": user["user_id"],
        "user": sanitized,
    }


# -------- Personal data --------
@app.get("/api/users/{user_id}")
def get_user(user_id: str):
    users = _load_json("personal_data.json")
    user = next((u for u in users if u.get("user_id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    sanitized = {k: v for k, v in user.items() if k != "password"}
    return {"user": sanitized}


# -------- Medications --------
@app.get("/api/users/{user_id}/medications")
def get_user_medications(user_id: str):
    data = _load_json("personal_medication.json")
    entry = next((u for u in data if u.get("user_id") == user_id), None)
    if not entry:
        return {"medications": []}

    meds: List[Dict[str, Any]] = []
    for i, m in enumerate(entry.get("medications", [])):
        name = f"{m.get('drug_name', 'Medication')}{f' {m.get('strength')}' if m.get('strength') else ''}".strip()
        freq = _format_frequency(m.get("schedule") or {})
        color = _hash_color(name)
        meds.append(
            {
                "id": i,
                "name": name,
                "frequency": freq,
                "pillsLeft": m.get("quantity_left", 0),
                "color": color,
            }
        )
    return {"medications": meds}


# Back-compat (default user 1)
@app.get("/api/medications")
def list_medications() -> dict:
    return get_user_medications("1")


# -------- Calendar (unchanged logic) --------
@app.get("/api/calendar/{calendar_id}/events")
def get_calendar_events(calendar_id: str) -> dict:
    try:
        events = get_events(calendar_id)
        if events:
            return {"events": events}
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


@app.post("/api/calendar/{calendar_id}/events/refresh")
def refresh_calendar_events(calendar_id: str) -> dict:
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
    uvicorn.run("Backend.api.server:app", host="0.0.0.0", port=8000, reload=True)