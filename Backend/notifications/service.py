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
from typing import Optional, Tuple
import openai
import hashlib

# Logger
logger = logging.getLogger("notifications")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s notifications: %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)
logger.propagate = False


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
      - there is a calendar event on the same day starting within <= 8 hours from now.
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
    window_event_end = now + timedelta(hours=8)
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
        description = (
            ev.get("description")
            or ev.get("details")
            or ev.get("notes")
            or ev.get("body")
            or ""
        )

        # Identify meds taken within the last 12 hours before the event start
        recent_meds = _get_recent_meds_before_event(start_dt, hours=12)
        med_names = sorted({m for m in recent_meds})

        mins_left = max(0, int((start_dt - now).total_seconds() // 60))
        hours = mins_left // 60
        minutes = mins_left % 60
        when_text = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        nid = f"eventsoon:{ev.get('id') or title}:{int(start_dt.timestamp())}"
        meds_text = (", ".join(med_names)) if med_names else "no recent meds"
        base_msg = f"You have '{title}' today in {when_text}. Recent meds (≤12h): {meds_text}."

        # Personalized LLM advice with caching (best-effort; optional)
        advice_key = _make_advice_cache_key(
            event_id=str(ev.get("id") or title),
            event_start=start_dt,
            event_title=title,
            event_description=description,
            medications=med_names,
        )
        advice = _advice_cache_get(advice_key)
        if advice:
            logger.info("LLM advice: using cached advice for key=%s", advice_key[:12])
        else:
            advice = _llm_personalized_event_advice(
                event_title=title,
                event_description=description,
                event_start=start_dt,
                medications=med_names,
            )
            if advice:
                _advice_cache_set(advice_key, advice)
                logger.info("LLM advice: cached new advice for key=%s", advice_key[:12])

        # Interactions temporarily disabled
        final_msg = base_msg
        if advice:
            final_msg = f"{final_msg} Advice: {advice}"
        final_msg = final_msg.strip()
        results.append(
            Notification(
                id=nid,
                category=NotificationCategory.EVENT_SOON,
                title="Event soon after your dose",
                message=final_msg,
                due_at=start_dt,
                color="brown",
                metadata={
                    "eventTitle": title,
                    "eventStartAt": start_dt.isoformat(),
                    "recentMeds": med_names,
                    "interactions": [],
                    "interactionsSkipped": True,
                    "eventDescription": description[:1000] if description else "",
                    "advice": advice,
                    "adviceKey": advice_key,
                },
            )
        )
    logger.info("Built %d event-soon notifications", len(results))
    return results


def _get_recent_meds_before_event(event_start: datetime, hours: int = 12) -> List[str]:
    """
    Return names of medications that have scheduled start times within (event_start - hours, event_start].
    """
    try:
        meds_events = get_medication_events()
    except Exception:
        logger.exception("Failed to load medication events for recent-meds computation")
        return []
    window_start = event_start - timedelta(hours=max(1, hours))
    names: List[str] = []
    for ev in meds_events:
        try:
            title = (ev.get("title") or "").strip()
            if not title:
                continue
            start_dt = _to_local_naive(_parse_iso((ev.get("start") or {}).get("date_time")))
            if not start_dt:
                continue
            if window_start < start_dt <= event_start:
                names.append(title)
        except Exception:
            continue
    return names


def _check_interactions_for_meds(med_names: List[str]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Best-effort check for interactions among a set of medication names by calling
    the drug_interactions helper. We call it for each med as 'new_drug' against the others.
    Returns a short summary and a detailed list (for metadata).
    """
    detail: List[Dict[str, Any]] = []
    if not med_names or len(med_names) < 2:
        return ("", detail)
    try:
        # Lazy import to avoid import-time failures
        from Backend.drug_interactions.drug_interactions import check_new_medication_against_list, InteractionReport  # type: ignore
    except Exception as exc:
        logger.info("Drug interactions module unavailable: %s", exc)
        return ("", detail)

    interactions_found = 0
    seen_pairs = set()
    for i, new_drug in enumerate(med_names):
        existing = [m for j, m in enumerate(med_names) if j != i]
        try:
            reports = check_new_medication_against_list(existing, new_drug) or []
        except Exception as exc:
            logger.info("Interaction check failed for %s vs list: %s", new_drug, exc)
            continue
        for new_name, existing_name, report in reports:
            pair_key = tuple(sorted([new_name, existing_name]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            interactions_found += 1
            try:
                # Pydantic model from module; safely convert
                if hasattr(report, "model_dump"):
                    rep = report.model_dump()
                else:
                    rep = {
                        "interaction_found": getattr(report, "interaction_found", True),
                        "severity": getattr(report, "severity", None),
                        "description": getattr(report, "description", None),
                        "extended_description": getattr(report, "extended_description", None),
                    }
            except Exception:
                rep = {"raw": str(report)}
            detail.append({
                "drugA": new_name,
                "drugB": existing_name,
                "report": rep,
            })

    if interactions_found == 0:
        return ("No interactions found among recent meds.", detail)
    if interactions_found == 1:
        return ("Potential interaction found among recent meds.", detail)
    return (f"{interactions_found} potential interactions found among recent meds.", detail)


def _build_llm_client() -> Optional[openai.OpenAI]:
    """
    Create an OpenAI client similar to camera_agent usage:
      - Requires OPENAI_API_KEY
      - Uses OPENAI_BASE_URL if provided (proxy), else defaults
    """
    try:
        key = 'sk-r0hwmHPWW8yghQ0_axmBfw'
        if not key:
            raise RuntimeError("No API key provided. Set OPENAI_API_KEY env var.")

        client = openai.OpenAI(
            api_key=key,
            base_url="https://fj7qg3jbr3.execute-api.eu-west-1.amazonaws.com/v1",
        )
        return client
    except Exception as exc:
        logger.info("Skipping LLM advice: failed to init client: %s", exc)
        return None


def _llm_personalized_event_advice(
    event_title: str,
    event_description: str,
    event_start: datetime,
    medications: List[str],
) -> str:
    """
    Ask an LLM for concise, practical advice given the event context and recent medications.
    Returns an empty string on failure or if LLM is not configured.
    """
    try:
        logger.info(
            "LLM advice: attempting for event='%s' start=%s meds=%s",
            event_title,
            event_start.isoformat(),
            ", ".join(medications) if medications else "none",
        )
        client = _build_llm_client()
        if client is None:
            logger.info("LLM advice: client not available (missing key or init failed)")
            return ""

        desc = (event_description or "").strip()
        if len(desc) > 600:
            desc = desc[:600] + "…"
        meds_list = ", ".join(medications) if medications else "None"
        start_iso = event_start.isoformat()

        system_prompt = (
            "You are a concise clinical assistant. Given an upcoming event and medications taken within the last 12 hours, "
            "provide ONE short sentence (<=180 chars) of precautionary advice. "
            "Err on the side of caution: prefer warnings over reassurance. "
            "Mention concrete risks (e.g., drowsiness, dehydration, sun sensitivity, bleeding, BP/HR changes) "
            "and clear avoidances (e.g., alcohol, driving, heavy exercise). "
            "No disclaimers; be direct and safety‑oriented."
        )
        user_prompt = (
            f"Event:\n"
            f"- Title: {event_title}\n"
            f"- Starts at: {start_iso}\n"
            f"- Description: {desc or 'n/a'}\n\n"
            f"Medications taken within 12h:\n"
            f"- {meds_list}\n\n"
            "Return only the advice sentence. Say if there are any warnings or precautions."
        )

        model ="gpt-5-nano"
        logger.info("LLM advice: calling model=%s base_url=%s", model, os.getenv("OPENAI_BASE_URL") or "default")
        # Prefer plain string messages for maximum compatibility
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        resp = client.chat.completions.create(model=model, messages=messages)
        content = resp.choices[0].message.content

        # content = (getattr(resp.choices[0].message, "content", "") or "").strip()
        # # Fallback: some gateways return content chunks as list
        # if not content:
        #     try:
        #         parts = resp.choices[0].message.content
        #         if isinstance(parts, list):
        #             texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"]
        #             content = " ".join([t for t in texts if t]).strip()
        #     except Exception:
        #         pass
        # If model returns nothing or a generic 'no concerns' answer, synthesize a conservative precaution
        # normalized = (content or "").lower().strip()
        # if (not content) or ("no specific concerns" in normalized) or ("no concerns" in normalized) or (len(normalized) < 12):
        #     # Heuristic, concise safety advice (<= 180 chars)
        #     # Include light personalization from event title and meds when possible
        #     meds_list_short = ", ".join(medications[:2]) + ("…" if len(medications) > 2 else "") if medications else ""
        #     hint = f" ({meds_list_short})" if meds_list_short else ""
        #     content = f"Be cautious{hint}: avoid alcohol; don't drive if drowsy; hydrate; avoid strenuous activity; monitor dizziness/BP/HR; seek help if symptoms worsen."
        logger.info("LLM advice: received content='%s'", content[:120].replace("\n", " "))
        if len(content) > 200:
            content = content[:200].rstrip() + "…"
        return content
    except Exception as exc:
        logger.info("LLM advice generation failed: %s", exc)
        return ""


# --------------- Advice cache (file-based) ---------------
_ADVICE_CACHE_PATH = os.getenv(
    "ADVICE_CACHE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "storage", "notifications_advice_cache.json"),
)


def _load_advice_cache() -> Dict[str, str]:
    try:
        path = os.path.abspath(_ADVICE_CACHE_PATH)
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_advice_cache(cache: Dict[str, str]) -> None:
    try:
        path = os.path.abspath(_ADVICE_CACHE_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception as exc:
        logger.info("Advice cache save failed: %s", exc)


def _advice_cache_get(key: str) -> Optional[str]:
    cache = _load_advice_cache()
    return cache.get(key)


def _advice_cache_set(key: str, value: str) -> None:
    cache = _load_advice_cache()
    cache[key] = value
    _save_advice_cache(cache)


def _make_advice_cache_key(
    event_id: str,
    event_start: datetime,
    event_title: str,
    event_description: str,
    medications: List[str],
) -> str:
    payload = {
        "eventId": event_id,
        "start": int(event_start.timestamp()),
        "title": event_title,
        # limit description length to avoid massive keys
        "desc": (event_description or "")[:256],
        "meds": sorted(medications or []),
        # include model in key to avoid cross-model reuse
        "model": "gpt-5-nano",
        "base_url": os.getenv("OPENAI_BASE_URL") or "default",
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"adv:{digest}"

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


