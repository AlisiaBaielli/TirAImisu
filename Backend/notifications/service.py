from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import os
import json
import logging

from Backend.notifications.models import Notification, NotificationCategory
from Backend.medications.repository import get_medication_events
from Backend.storage.events import get_events as get_cached_events, set_events as set_cached_events
from datetime import timezone

# Logger
logger = logging.getLogger("notifications")


def _now() -> datetime:
    return datetime.now()

_LOCAL_TZ = datetime.now().astimezone().tzinfo


def _to_local_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    try:
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(_LOCAL_TZ).replace(tzinfo=None)
    except Exception:
        return dt

def _load_personal_medications(user_id: str = "1") -> List[Dict[str, Any]]:
    """
    Load raw medication rows for a given user from Backend/data/personal_medication.json.
    """
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "personal_medication.json")
    if not os.path.exists(data_path):
        logger.warning("personal_medication.json not found at %s", data_path)
        return []
    try:
        with open(data_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        logger.exception("Failed to load personal_medication.json from %s", data_path)
        return []
    entry = next((u for u in data if str(u.get("user_id")) == str(user_id)), None)
    if not entry:
        logger.info("No entry for user_id=%s in personal_medication.json", user_id)
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
    logger.debug("Building reminder notifications at now=%s", now.isoformat())
    upcoming: List[Notification] = []
    events = get_medication_events()
    logger.debug("Loaded %d medication events", len(events))
    window_start = now
    window_end = now + timedelta(minutes=30)

    for ev in events:
        try:
            start_iso = ev.get("start", {}).get("date_time")
            if not start_iso:
                continue
            start_dt = _to_local_naive(_parse_iso(start_iso))
            if not start_dt:
                continue
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
            logger.exception("Error while processing reminder event: %s", ev)
            continue
    logger.info("Built %d reminder notifications", len(upcoming))
    return upcoming


def _build_low_stock_notifications(now: datetime) -> List[Notification]:
    """
    Create notifications for medications projected to run out within 7 days (inclusive).
    """
    logger.debug("Building low stock notifications at now=%s", now.isoformat())
    warnings: List[Notification] = []
    meds = _load_personal_medications()
    logger.debug("Loaded %d raw medications for low stock check", len(meds))
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
            logger.exception("Error while processing low stock for medication: %s", m)
            continue
    logger.info("Built %d low stock notifications", len(warnings))
    return warnings


def _load_calendar_events(now: datetime) -> List[Dict[str, Any]]:
    """
    Load user's general calendar events from cache or upstream.
    Uses EVENTS_CALENDAR_ID env var.
    Returns a list of events with {"title", "start": {"date_time"}, "end": {"date_time"}, "id"} shape.
    """
    calendar_id = os.getenv("EVENTS_CALENDAR_ID")
    if not calendar_id:
        logger.info("EVENTS_CALENDAR_ID not set; skipping external events")
        return []
    try:
        events = get_cached_events(calendar_id) or []
        if events:
            logger.debug("Loaded %d events from cache for %s", len(events), calendar_id)
            return events
        try:
            from Backend.calendar.cal_api import list_events as live_list_events  # lazy import
            live = live_list_events(calendar_id)
            if isinstance(live, list):
                set_cached_events(calendar_id, live)
                logger.debug("Fetched %d live events for %s and cached", len(live), calendar_id)
                return live
        except Exception:
            logger.exception("Live fetch of calendar events failed for %s", calendar_id)
            return []
    except Exception:
        logger.exception("Failed to load cached events for %s", calendar_id)
        return []


def _parse_iso(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


def _build_event_soon_notifications(now: datetime) -> List[Notification]:
    """
    Create notifications when:
      - there is any medication scheduled today (past or future), AND
      - there is a calendar event on the same day starting within <= 3 hours from now.
    One notification per qualifying calendar event.
    """
    logger.debug("Building event-soon notifications at now=%s", now.isoformat())
    meds = get_medication_events()
    logger.debug("Loaded %d medication events for today-check", len(meds))
    has_med_today = False
    for ev in meds:
        start_dt = _to_local_naive(_parse_iso((ev.get("start") or {}).get("date_time")))
        if not start_dt:
            continue
        if start_dt.date() == now.date():
            has_med_today = True
            break
    # Require any medication scheduled today
    if not has_med_today:
        logger.info("No medication scheduled today; skipping event-soon notifications")
        return []

    events = _load_calendar_events(now)
    if not events:
        logger.info("No external calendar events available; skipping event-soon notifications")
        return []
    window_event_end = now + timedelta(hours=3)
    results: List[Notification] = []
    for ev in events:
        start_dt = _to_local_naive(_parse_iso((ev.get("start") or {}).get("date_time")))
        if not start_dt:
            continue
        # same-day constraint and within next 3 hours
        if start_dt.date() != now.date():
            continue
        if not (now <= start_dt <= window_event_end):
            continue
        title = (ev.get("title") or ev.get("summary") or "Event")
        mins_left = max(0, int((start_dt - now).total_seconds() // 60))
        hours = mins_left // 60
        minutes = mins_left % 60
        when_text = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        nid = f"eventsoon:{ev.get('id') or title}:{int(start_dt.timestamp())}"
        results.append(
            Notification(
                id=nid,
                category=NotificationCategory.EVENT_SOON,
                title="Event soon after your dose",
                message=f"You have '{title}' today in {when_text}.",
                due_at=start_dt,
                color="brown",
                metadata={
                    "eventTitle": title,
                    "eventStartAt": start_dt.isoformat(),
                },
            )
        )
    logger.info("Built %d event-soon notifications", len(results))
    return results


def get_notifications() -> Dict[str, List[Dict[str, Any]]]:
    """
    Public API to fetch notifications payload for the frontend.
    Returns a dict with a 'notifications' list of serialized Notification objects.
    """
    now = _now()
    reminders = _build_reminder_notifications(now)
    low_stock = _build_low_stock_notifications(now)
    logger.info("Building notifications payload at %s", now.isoformat())
    event_soon = _build_event_soon_notifications(now)
    all_items = reminders + low_stock + event_soon

    def _sort_key(dt: datetime) -> float:
        try:
            # Use epoch seconds; handles both naive and aware datetimes
            return dt.timestamp()
        except Exception:
            try:
                return dt.replace(tzinfo=timezone.utc).timestamp()
            except Exception:
                return 0.0

    try:
        all_items.sort(key=lambda n: _sort_key(n.due_at))
    except Exception:
        logger.exception("Sorting notifications failed; proceeding unsorted")
    # Ensure datetime fields are JSON-serializable
    payload = {"notifications": [n.model_dump(mode="json") for n in all_items]}
    logger.info(
        "Notifications built: total=%d (reminders=%d, low_stock=%d, event_soon=%d)",
        len(all_items),
        len([x for x in all_items if x.category == NotificationCategory.REMINDER]),
        len([x for x in all_items if x.category == NotificationCategory.LOW_STOCK]),
        len([x for x in all_items if x.category == NotificationCategory.EVENT_SOON]),
    )
    return payload


