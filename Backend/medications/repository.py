from typing import List, Optional, Dict, Any
from Backend.medications.medication import Medication
import os
import json
from datetime import datetime, timedelta, date


def _get_personal_json_path() -> str:
    """
    Resolve personal medications JSON path.
    Priority:
    - PERSONAL_MEDICATION_JSON_PATH env var
    - Default: Backend/data/personal_medication.json
    """
    env_path = os.getenv("PERSONAL_MEDICATION_JSON_PATH")
    if env_path:
        return env_path
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "personal_medication.json")


def _get_user_id() -> str:
    """
    Resolve which user_id to read from the JSON.
    Priority:
    - PERSONAL_MED_USER_ID env var
    - Default: "1"
    """
    return os.getenv("PERSONAL_MED_USER_ID", "1")


def _load_json(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _save_json(path: str, data: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_current_medications() -> List[Medication]:
    """
    Read medications from personal_medication.json and convert to Medication instances.
    The JSON schema is a list of user objects:
    [
      { "user_id": "1", "medications": [ { "drug_name": "...", "strength": "...", "schedule": { ... }, ... } ] }
    ]
    """
    json_path = _get_personal_json_path()
    user_id = _get_user_id()
    doc = _load_json(json_path)

    user_entry = next((u for u in doc if str(u.get("user_id")) == str(user_id)), None)
    if not user_entry:
        return []

    meds_json = user_entry.get("medications", []) or []
    medications: List[Medication] = []

    def parse_time_to_hour(val: str) -> int:
        try:
            hh = int((val or "0").split(":")[0])
            return max(0, min(23, hh))
        except Exception:
            return 8

    for idx, m in enumerate(meds_json, start=1):
        drug_name = str(m.get("drug_name", "")).strip()
        strength = str(m.get("strength", "")).strip()
        schedule = m.get("schedule") or {}
        sched_type = str(schedule.get("type", "daily")).lower()

        hour_interval = 24
        time_hour = 8
        if sched_type == "daily":
            times = schedule.get("times") or []
            if isinstance(times, list) and times:
                time_hour = parse_time_to_hour(times[0])
            hour_interval = 24
        elif sched_type == "weekly":
            time_str = schedule.get("time") or "08:00"
            time_hour = parse_time_to_hour(time_str)
            hour_interval = 168
        else:
            # Fallback for as_needed etc.
            time_hour = 8
            hour_interval = 24

        name = f"{drug_name} {strength}".strip()
        medications.append(
            Medication(
                id=str(idx),
                name=name,
                time=time_hour,
                color="med-blue",
                hour_interval=hour_interval,
                description=None,
            )
        )

    return medications


def _next_id(existing: List[Medication]) -> str:
    max_id = 0
    for m in existing:
        try:
            max_id = max(max_id, int(str(m.id)))
        except Exception:
            continue
    return str(max_id + 1)


def add_medication(
    name: str,
    time: int,
    color: str,
    hour_interval: int,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
) -> Medication:
    """
    Append a new medication to the personal_medication.json under the selected user and return the created Medication.
    The JSON entry will be normalized with:
      drug_name, strength (best-effort split), schedule.type ("daily" or "weekly"), schedule.times/time, start_date
    """
    json_path = _get_personal_json_path()
    user_id = _get_user_id()

    doc = _load_json(json_path)
    user_entry = next((u for u in doc if str(u.get("user_id")) == str(user_id)), None)
    if not user_entry:
        user_entry = {"user_id": str(user_id), "medications": []}
        doc.append(user_entry)

    meds = user_entry.get("medications") or []

    # Best-effort split name -> drug_name + strength (split at last space)
    drug_name = name
    strength = ""
    if " " in name.strip():
        parts = name.strip().rsplit(" ", 1)
        if len(parts) == 2 and any(ch.isdigit() for ch in parts[1]):
            drug_name, strength = parts[0], parts[1]

    # Schedule mapping from hour_interval
    if int(hour_interval) >= 168:
        schedule = {"type": "weekly", "day": "Sunday", "time": f"{int(time):02d}:00"}
    else:
        schedule = {"type": "daily", "times": [f"{int(time):02d}:00"]}

    new_entry: Dict[str, Any] = {
        "drug_name": drug_name,
        "strength": strength,
        "quantity_left": 30,
        "dose_per_intake": 1,
        "schedule": schedule,
        "start_date": start_date or os.getenv("PERSONAL_MED_START_DATE", "2025-11-08"),
    }
    meds.append(new_entry)
    user_entry["medications"] = meds

    _save_json(json_path, doc)

    # Return Medication DTO
    current = get_current_medications()
    new_id = _next_id(current)
    return Medication(
        id=new_id,
        name=name,
        time=int(time),
        color=color,
        hour_interval=int(hour_interval),
        description=description,
    )


def get_medication_events() -> List[Dict[str, Any]]:
    """
    Expand medications from personal_medication.json into event-like objects:
    { title, start: { date_time }, end: { date_time } }
    Using:
      - hour from schedule ('times'[0] or 'time')
      - start_date for the first occurrence
      - quantity_left as the number of occurrences
      - daily -> +24h; weekly -> +168h between occurrences
      - duration 10 minutes
    """
    json_path = _get_personal_json_path()
    user_id = _get_user_id()
    doc = _load_json(json_path)

    user_entry = next((u for u in doc if str(u.get("user_id")) == str(user_id)), None)
    if not user_entry:
        return []

    meds_json = user_entry.get("medications", []) or []
    results: List[Dict[str, Any]] = []

    def parse_time_to_hour(val: str) -> int:
        try:
            hh = int((val or "0").split(":")[0])
            return max(0, min(23, hh))
        except Exception:
            return 8

    for m in meds_json:
        drug_name = str(m.get("drug_name", "")).strip()
        strength = str(m.get("strength", "")).strip()
        schedule = m.get("schedule") or {}
        sched_type = str(schedule.get("type", "daily")).lower()
        qty_left = m.get("quantity_left", 1)
        try:
            occurrences = max(1, int(qty_left))
        except Exception:
            occurrences = 1

        hour_interval = 24
        time_hour = 8
        if sched_type == "daily":
            times = schedule.get("times") or []
            if isinstance(times, list) and times:
                time_hour = parse_time_to_hour(times[0])
            hour_interval = 24
        elif sched_type == "weekly":
            time_str = schedule.get("time") or "08:00"
            time_hour = parse_time_to_hour(time_str)
            hour_interval = 168
        else:
            time_hour = 8
            hour_interval = 24

        start_date_str = m.get("start_date")
        if start_date_str:
            try:
                start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except Exception:
                start_date_obj = date.today()
        else:
            start_date_obj = date.today()

        base_start = datetime(
            year=start_date_obj.year,
            month=start_date_obj.month,
            day=start_date_obj.day,
            hour=time_hour,
            minute=0,
        )
        title = f"{drug_name} {strength}".strip()

        for i in range(occurrences):
            start_dt = base_start + timedelta(hours=i * hour_interval)
            end_dt = start_dt + timedelta(minutes=10)
            results.append(
                {
                    "id": f"med-{drug_name}-{i}-{int(start_dt.timestamp())}",
                    "title": title or "Medication",
                    "start": {"date_time": start_dt.isoformat()},
                    "end": {"date_time": end_dt.isoformat()},
                }
            )

    return results


def _split_name(name: str) -> tuple[str, str]:
    name = (name or "").strip()
    if " " in name:
        parts = name.rsplit(" ", 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
    return name, ""


def upsert_scanned_medication(
    name: str,
    quantity: int,
    time: Optional[int] = None,
    hour_interval: Optional[int] = None,
    start_date: Optional[str] = None,
) -> Medication:
    """
    If medication (drug_name + strength) exists for the current user, increment its quantity_left.
    Otherwise, create a new entry with the provided quantity and basic schedule inferred from time/hour_interval.
    Returns a Medication DTO representing the upserted medication (best-effort).
    """
    json_path = _get_personal_json_path()
    user_id = _get_user_id()
    doc = _load_json(json_path)
    user_entry = next((u for u in doc if str(u.get("user_id")) == str(user_id)), None)
    if not user_entry:
        user_entry = {"user_id": str(user_id), "medications": []}
        doc.append(user_entry)
    meds = user_entry.get("medications") or []

    drug_name, strength = _split_name(name)
    idx = None
    for i, m in enumerate(meds):
        if str(m.get("drug_name", "")).strip().lower() == drug_name.lower() and str(m.get("strength", "")).strip().lower() == strength.lower():
            idx = i
            break

    qty_to_add = max(0, int(quantity or 0))
    if idx is not None:
        # Update existing
        current_qty = int(meds[idx].get("quantity_left", 0) or 0)
        meds[idx]["quantity_left"] = current_qty + qty_to_add
        user_entry["medications"] = meds
        _save_json(json_path, doc)
    else:
        # Add new with given quantity and inferred schedule
        inferred_hour_interval = int(hour_interval) if hour_interval is not None else 24
        inferred_time = int(time) if time is not None else 8
        schedule = (
            {"type": "weekly", "day": "Sunday", "time": f"{inferred_time:02d}:00"}
            if inferred_hour_interval >= 168
            else {"type": "daily", "times": [f"{inferred_time:02d}:00"]}
        )
        new_entry: Dict[str, Any] = {
            "drug_name": drug_name,
            "strength": strength,
            "quantity_left": qty_to_add,
            "dose_per_intake": 1,
            "schedule": schedule,
            "start_date": start_date or os.getenv("PERSONAL_MED_START_DATE", date.today().strftime("%Y-%m-%d")),
        }
        meds.append(new_entry)
        user_entry["medications"] = meds
        _save_json(json_path, doc)

    # Return DTO based on current list
    meds_list = get_current_medications()
    # Try to find matching DTO
    dto = next((m for m in meds_list if m.name.strip().lower() == f"{drug_name} {strength}".strip().lower()), None)
    if dto:
        return dto
    # Fallback DTO
    return Medication(
        id=_next_id(meds_list),
        name=f"{drug_name} {strength}".strip(),
        time=int(time or 8),
        color="med-blue",
        hour_interval=int(hour_interval or 24),
        description=None,
    )