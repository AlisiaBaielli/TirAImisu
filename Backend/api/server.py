from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import json
import os
import uuid
from datetime import datetime, timedelta, date
from fastapi import status

from Backend.storage.events import get_events, set_events
from Backend.medications.repository import get_current_medications, add_medication, get_medication_events
from Backend.calendar.cal_tools import create_recurring_events
from Backend.agents.camera_agent.agent import CameraAgent
from Backend.data.utils import add_new_medication  # NEW

app = FastAPI(title="PillPal API", version="1.0.0")

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

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
def login(payload: LoginRequest):
    users = _load_json("personal_data.json")
    user = next(
        (u for u in users if u.get("username") == payload.username and u.get("password") == payload.password),
        None,
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    sanitized = {k: v for k, v in user.items() if k not in ["password"]}
    return {"user_id": user["user_id"], "user": sanitized}

@app.get("/api/users/{user_id}")
def get_user(user_id: str):
    users = _load_json("personal_data.json")
    user = next((u for u in users if u.get("user_id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    sanitized = {k: v for k, v in user.items() if k != "password"}
    return {"user": sanitized}

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

@app.get("/api/medications")
def list_medications_backcompat() -> dict:
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
    meds = [m.to_dict() for m in get_current_medications()]
    return {"medications": meds}

class MedicationCreate(BaseModel):
    name: str = Field(..., min_length=1)
    time: int = Field(..., ge=0, le=23)
    color: str = Field("med-blue")
    hour_interval: int = Field(24, ge=1)
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    occurrences: Optional[int] = Field(None, ge=1)

@app.post("/api/medications")
def create_medication(payload: MedicationCreate) -> dict:
    med = add_medication(
        name=payload.name.strip(),
        time=payload.time,
        color=payload.color.strip(),
        hour_interval=payload.hour_interval,
        description=payload.description.strip() if payload.description else None,
        start_date=payload.start_date,
    )
    try:
        calendar_id = os.getenv("CALENDAR_ID") or os.getenv("DEFAULT_CALENDAR_ID")
        if calendar_id:
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
            occ = payload.occurrences
            if not occ and payload.end_date:
                try:
                    end_date_obj = datetime.strptime(payload.end_date, "%Y-%m-%d").date()
                    total_hours = (
                        datetime.combine(end_date_obj, datetime.min.time())
                        - datetime.combine(start_date_obj, datetime.min.time())
                    ).days * 24
                    occ = max(1, (total_hours // med.hour_interval) + 1)
                except Exception:
                    occ = None
            if not occ:
                occ = 7
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
        pass
    return {"medication": med.to_dict()}

@app.get("/api/medications/events")
def list_medication_events() -> dict:
    events = get_medication_events()
    return {"events": events}

@app.get("/api/events-calendar/events")
def get_events_calendar_events() -> dict:
    calendar_id = os.getenv("EVENTS_CALENDAR_ID")
    if not calendar_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="EVENTS_CALENDAR_ID env var not set")
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

@app.post("/api/events-calendar/events/refresh")
def refresh_events_calendar_events() -> dict:
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

# ─────────── Camera scan endpoint persists result using utils ─────────── #
class CameraScanRequest(BaseModel):
    user_id: str
    image_b64: str

class CameraScanResponse(BaseModel):
    medication_name: Optional[str]
    dosage: Optional[str]
    num_pills: Optional[int]

camera_agent = CameraAgent()

@app.post("/api/camera-agent/scan", response_model=CameraScanResponse)
def camera_agent_scan(payload: CameraScanRequest):
    """
    Accepts base64 image, runs the CameraAgent pipeline, returns extracted fields,
    and saves the medication into personal_medication.json using utils.
    """
    if not payload.image_b64:
        raise HTTPException(status_code=400, detail="image_b64 required")
    try:
        result = camera_agent.graph.invoke(
            {
                "user_id": payload.user_id,
                "image_b64": payload.image_b64,
                "activity": [],
            },
            config={"configurable": {"thread_id": f"scan-{payload.user_id}-{uuid.uuid4()}"}},
        )
    except Exception:
        result = camera_agent.run(json.dumps({"user_id": payload.user_id, "image_b64": payload.image_b64}))

    extracted = result.get("extracted") or {}
    med_name = extracted.get("medication_name")
    dosage = extracted.get("dosage")
    num_pills = extracted.get("num_pills")

    # Persist via utils if we have at least a name
    if med_name:
        new_med = {
            "drug_name": med_name,
            "strength": dosage or "",
            "quantity_left": num_pills if isinstance(num_pills, int) else 0,
            "dose_per_intake": 1,
            "schedule": {},  # user can set scheduling later
            "start_date": date.today().isoformat(),
        }
        try:
            add_new_medication(payload.user_id, new_med)
        except Exception:
            # Do not block response on save failure
            pass

    return CameraScanResponse(
        medication_name=med_name,
        dosage=dosage,
        num_pills=num_pills,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("Backend.api.server:app", host="0.0.0.0", port=8000, reload=True)