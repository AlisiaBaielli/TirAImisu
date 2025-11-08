from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, date
from fastapi import status
import json
import os
import uuid
import logging

from Backend.agents.purchasing_agent.agent import run_checkout
from Backend.storage.events import get_events, set_events
from Backend.medications.repository import (
    get_current_medications,
    add_medication,
    get_medication_events,
)
from Backend.calendar.cal_tools import create_recurring_events
from Backend.notifications.service import get_notifications as build_notifications
from Backend.agents.camera_agent.agent import CameraAgent
from Backend.data.utils import add_new_medication, retrieve_medications, ensure_colors
from Backend.agents.camera_agent.email_doctor import send_email_to_doctor

# import drug interactions tools
from Backend.drug_interactions.drug_interactions import (
    check_new_medication_against_list,
    get_drug_side_effects,
)

app = FastAPI(title="PillPal API", version="1.0.0")
logger = logging.getLogger("api")

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


def _format_frequency(schedule: Dict[str, Any]) -> str:
    t = (schedule or {}).get("type")
    if t == "daily":
        times = schedule.get("times", [])
        return f"daily at {', '.join(times)}" if times else "daily"
    if t == "weekly":
        day = schedule.get("day") or schedule.get("days")
        times = schedule.get("times", [])
        if day and times:
            return f"weekly on {day} at {', '.join(times)}"
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
        (
            u
            for u in users
            if u.get("username") == payload.username
            and u.get("password") == payload.password
        ),
        None,
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    sanitized = {k: v for k, v in user.items() if k != "password"}
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
    try:
        ensure_colors(user_id)
    except Exception:
        pass

    meds_raw = retrieve_medications(user_id)
    if not meds_raw:
        return {"medications": []}

    meds: List[Dict[str, Any]] = []
    for i, m in enumerate(meds_raw):
        name = f"{m.get('drug_name', 'Medication')}{' ' + m.get('strength') if m.get('strength') else ''}".strip()
        freq = _format_frequency(m.get("schedule") or {})
        color = m.get("color") or "med-blue"
        meds.append(
            {
                "id": i,
                "name": name,
                "frequency": freq,
                "pillsLeft": m.get("quantity_left", 0),
                "color": color,
                "schedule": m.get("schedule", {}),
                "start_date": m.get("start_date"),
                "end_date": m.get("end_date"),
                "strength": m.get("strength", ""),
            }
        )
    return {"medications": meds}


@app.post("/api/users/{user_id}/medications")
def add_user_medication(user_id: str, payload: Dict[str, Any]):
    """
    Persist medication into Backend/data/personal_medication.json using add_new_medication.
    Accepts payload with fields:
      - drug_name (string) OR name
      - strength (string) OR dosage
      - quantity_left (int) OR numberOfPills
      - schedule: optional dict {type: 'daily'|'weekly'|'as_needed', times: ['HH:mm'], day/day(s)}
      - start_date, end_date
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    # normalize inputs
    drug_name = payload.get("drug_name") or payload.get("name")
    strength = payload.get("strength") or payload.get("dosage") or ""
    qty = payload.get("quantity_left") or payload.get("numberOfPills") or 0
    start_date = payload.get("start_date") or payload.get("startDate")
    end_date = payload.get("end_date") or payload.get("endDate")

    schedule = payload.get("schedule")
    # If schedule absent but frequency/time provided, build schedule
    if not schedule:
        freq = payload.get("frequency")
        time = payload.get("time")
        if freq:
            schedule = {"type": freq}
            if isinstance(time, str) and time:
                schedule["times"] = [time]
            elif isinstance(time, int):
                # convert int hour to HH:MM
                schedule["times"] = [f"{int(time):02d}:00"]
    med = {
        "drug_name": str(drug_name).strip() if drug_name else None,
        "strength": str(strength).strip() if strength else "",
        "quantity_left": (
            int(qty)
            if isinstance(qty, (int, float, str)) and str(qty).strip() != ""
            else 0
        ),
        "dose_per_intake": (
            int(payload.get("dose_per_intake", 1))
            if payload.get("dose_per_intake")
            else 1
        ),
        "schedule": schedule or {},
        "start_date": start_date,
        "end_date": end_date,
        "color": payload.get("color"),
    }

    if not med["drug_name"]:
        raise HTTPException(status_code=400, detail="drug_name required")

    try:
        add_new_medication(user_id, med)
    except Exception as exc:
        logger.exception("Failed to persist medication")
        raise HTTPException(status_code=500, detail=str(exc))

    return {"ok": True, "medication": med}


@app.get("/api/notifications")
def list_notifications() -> dict:
    try:
        return build_notifications()
    except Exception as exc:
        logger.exception("Failed to build notifications")
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
                start_date_obj = datetime.strptime(
                    payload.start_date, "%Y-%m-%d"
                ).date()
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
                    end_date_obj = datetime.strptime(
                        payload.end_date, "%Y-%m-%d"
                    ).date()
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EVENTS_CALENDAR_ID env var not set",
        )
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EVENTS_CALENDAR_ID env var not set",
        )
    try:
        from Backend.calendar.cal_api import list_events as live_list_events

        live = live_list_events(calendar_id)
        if not isinstance(live, list):
            raise HTTPException(
                status_code=502, detail="Invalid events format from upstream"
            )
        set_events(calendar_id, live)
        return {"events": live}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/buy")
@app.post("/api/buy")
async def buy(data: dict):
    drug_name = data.get("drug_name")
    if not drug_name:
        raise HTTPException(status_code=400, detail="drug_name is required")
    result = await run_checkout(user_id="1", drug_name=drug_name)
    return {"ok": True, "ordered": drug_name, "result": result}


# Camera scan endpoint left unchanged...
class CameraScanRequest(BaseModel):
    user_id: str
    image_b64: str


class CameraScanResponse(BaseModel):
    medication_name: Optional[str]
    dosage: Optional[str]
    num_pills: Optional[int]
    color: Optional[str]


camera_agent = CameraAgent()


@app.post("/api/camera-agent/scan", response_model=CameraScanResponse)
def camera_agent_scan(payload: CameraScanRequest):
    if not payload.image_b64:
        raise HTTPException(status_code=400, detail="image_b64 required")
    try:
        result = camera_agent.graph.invoke(
            {
                "user_id": payload.user_id,
                "image_b64": payload.image_b64,
                "activity": [],
            },
            config={
                "configurable": {"thread_id": f"scan-{payload.user_id}-{uuid.uuid4()}"}
            },
        )
    except Exception:
        result = camera_agent.run(
            json.dumps({"user_id": payload.user_id, "image_b64": payload.image_b64})
        )

    extracted = result.get("extracted") or {}
    med_name = extracted.get("medication_name")
    dosage = extracted.get("dosage")
    num_pills = extracted.get("num_pills")

    color_assigned = None
    if med_name:
        new_med = {
            "drug_name": med_name,
            "strength": dosage or "",
            "quantity_left": num_pills if isinstance(num_pills, int) else 0,
            "dose_per_intake": 1,
            "schedule": {},
            "start_date": date.today().isoformat(),
        }
        try:
            add_new_medication(payload.user_id, new_med)
            meds = retrieve_medications(payload.user_id)
            for m in reversed(meds):
                if m.get("drug_name") == med_name and (m.get("strength") or "") == (
                    dosage or ""
                ):
                    color_assigned = m.get("color")
                    break
        except Exception:
            pass

    return CameraScanResponse(
        medication_name=med_name,
        dosage=dosage,
        num_pills=num_pills,
        color=color_assigned,
    )


# Drug interactions endpoint unchanged (calls check_new_medication_against_list)
class DrugInteractionRequest(BaseModel):
    user_id: str
    new_medication_name: str


@app.post("/api/drug-interactions")
def drug_interactions_check(payload: DrugInteractionRequest):
    user_id = payload.user_id
    new_med = payload.new_medication_name
    if not user_id or not new_med:
        raise HTTPException(
            status_code=400, detail="user_id and new_medication_name required"
        )

    existing = retrieve_medications(user_id)
    existing_names: List[str] = []
    for m in existing:
        name = (m.get("drug_name") or "").strip()
        if name:
            existing_names.append(name)

    try:
        results = check_new_medication_against_list(existing_names, new_med)
        side_effects = get_drug_side_effects(new_med)
    except Exception as exc:
        logger.exception("Failed to send email to doctor")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(exc)}"
        )

    out = []
    for new_d, existing_d, report in results:
        out.append(
            {
                "new_drug": new_d,
                "existing_drug": existing_d,
                "interaction_found": bool(getattr(report, "interaction_found", False)),
                "severity": getattr(report, "severity", None),
                "description": getattr(report, "description", None),
                "extended_description": getattr(report, "extended_description", None),
            }
        )

    return {"interactions": out}

class SendEmailRequest(BaseModel):
    user_id: int = Field(1, ge=1)
    content: str = Field(..., min_length=1)


class SendEmailResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    to: Optional[str] = None
    from_email: Optional[str] = Field(None, alias="from")
    subject: Optional[str] = None
    error: Optional[str] = None


@app.post("/api/send-email-to-doctor", response_model=SendEmailResponse)
def send_email_endpoint(payload: SendEmailRequest):
    try:
        result = send_email_to_doctor(user_id=payload.user_id, content=payload.content)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to send email")
            )
        
        return SendEmailResponse(
            success=result["success"],
            message_id=result.get("message_id"),
            to=result.get("to"),
            from_email=result.get("from"),
            subject=result.get("subject"),
        )
    except HTTPException:
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("Backend.api.server:app", host="0.0.0.0", port=8000, reload=True)
