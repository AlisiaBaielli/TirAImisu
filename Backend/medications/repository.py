from typing import List, Optional, Dict, Any
from Backend.medications.medication import Medication
import os
import json


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
