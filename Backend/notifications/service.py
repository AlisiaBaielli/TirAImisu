from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import os
import json

from Backend.notifications.models import Notification, NotificationCategory
from Backend.medications.repository import get_medication_events


def _now() -> datetime:
    return datetime.now()


def _load_personal_medications(user_id: str = "1") -> List[Dict[str, Any]]:
    """
    Load raw medication rows for a given user from Backend/data/personal_medication.json.
    """
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "personal_medication.json")
    if not os.path.exists(data_path):
        return []
    try:
        data = json.loads(open(data_path, "r", encoding="utf-8").read())
    except Exception:
        return []
    entry = next((u for u in data if str(u.get("user_id")) == str(user_id)), None)
    if not entry:
        return []
    meds = entry.get("medications", []) or []
    return meds


def _intakes_left(quantity_left: int | float, dose_per_intake: int | float) -> int:
    try:
        q = float(quantity_left)
        d = max(1.0, float(dose_per_intake or 1))
        return max(0, int(q // d))
    except Exception:
        return 0


def _per_day_intakes(schedule: Dict[str, Any]) -> float:
    """
    Estimate number of intakes per day from schedule.
    Supports:
      - { type: "daily", times: [...] }
      - { type: "weekly", times: [...] }  (treated as evenly spread; /7)
    """
    t = str((schedule or {}).get("type", "daily")).lower()
    times = schedule.get("times") or []
    if t == "daily":
        return float(max(1, len(times) if isinstance(times, list) and len(times) > 0 else 1))
    if t == "weekly":
        per_week = float(max(1, len(times) if isinstance(times, list) and len(times) > 0 else 1))
        return per_week / 7.0
    # Fallback: assume daily once
    return 1.0


def _estimate_runout_date(m: Dict[str, Any], base_date: datetime) -> Tuple[datetime | None, int]:
    """
    Estimate run-out date based on quantity_left, dose_per_intake and schedule.
    Returns tuple: (runout_date, days_left)
    """
    qty = m.get("quantity_left", 0)
    dose = m.get("dose_per_intake", 1)
    schedule = m.get("schedule") or {}

    intakes_remaining = _intakes_left(qty, dose)
    per_day = _per_day_intakes(schedule)
    if per_day <= 0.0:
        return (None, 0)
    days_left_float = intakes_remaining / per_day
    days_left = int(days_left_float) if days_left_float.is_integer() else int(days_left_float) + 1
    runout_date = (base_date + timedelta(days=days_left)).replace(hour=8, minute=0, second=0, microsecond=0)
    return (runout_date, max(0, days_left))


def _build_reminder_notifications(now: datetime) -> List[Notification]:
    """
    Create notifications for doses starting within the next 30 minutes.
    Source: get_medication_events() expanded from personal_medication.json
    """
    upcoming: List[Notification] = []
    events = get_medication_events()
    window_start = now
    window_end = now + timedelta(minutes=30)

    for ev in events:
        try:
            start_iso = ev.get("start", {}).get("date_time")
            if not start_iso:
                continue
            start_dt = datetime.fromisoformat(start_iso)
            if start_dt < window_start or start_dt > window_end:
                continue
            title = ev.get("title") or "Medication"
            nid = f"reminder:{ev.get('id') or title}:{int(start_dt.timestamp())}"
            message = f"It's almost time to take {title} at {start_dt.strftime('%H:%M')}."
            upcoming.append(
                Notification(
                    id=nid,
                    category=NotificationCategory.REMINDER,
                    title="Upcoming dose",
                    message=message,
                    due_at=start_dt,
                    color="blue",
                    metadata={
                        "medicationName": title,
                        "eventId": ev.get("id"),
                        "startAt": start_dt.isoformat(),
                    },
                )
            )
        except Exception:
            continue
    return upcoming


def _build_low_stock_notifications(now: datetime) -> List[Notification]:
    """
    Create notifications for medications projected to run out within 7 days (inclusive).
    """
    warnings: List[Notification] = []
    meds = _load_personal_medications()
    for m in meds:
        try:
            drug_name = str(m.get("drug_name", "")).strip()
            strength = str(m.get("strength", "")).strip()
            title_name = f"{drug_name} {strength}".strip() or "Medication"
            runout_date, days_left = _estimate_runout_date(m, now)
            if not runout_date:
                continue
            if 0 < days_left <= 7:
                nid = f"lowstock:{drug_name}:{int(runout_date.timestamp())}"
                when_text = "in 1 day" if days_left == 1 else f"in {days_left} days"
                message = f"You will run out of {title_name} {when_text}."
                warnings.append(
                    Notification(
                        id=nid,
                        category=NotificationCategory.LOW_STOCK,
                        title="Running low",
                        message=message,
                        due_at=runout_date,
                        color="red",
                        metadata={
                            "medicationName": title_name,
                            "daysLeft": days_left,
                            "runoutDate": runout_date.isoformat(),
                        },
                    )
                )
        except Exception:
            continue
    return warnings


def get_notifications() -> Dict[str, List[Dict[str, Any]]]:
    """
    Public API to fetch notifications payload for the frontend.
    Returns a dict with a 'notifications' list of serialized Notification objects.
    """
    now = _now()
    reminders = _build_reminder_notifications(now)
    low_stock = _build_low_stock_notifications(now)
    all_items = reminders + low_stock
    all_items.sort(key=lambda n: n.due_at)
    return {"notifications": [n.model_dump() for n in all_items]}


