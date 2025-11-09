import json
import os
from typing import List, Dict, Any, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEDICATION_FILE = os.path.join(SCRIPT_DIR, "personal_medication.json")
USER_DATA_FILE = os.path.join(SCRIPT_DIR, "personal_data.json")
PALETTE = [
    "med-blue",
    "med-green",
    "med-orange",
    "med-purple",
    "med-pink",
    "med-yellow",
]


def _read_json(filepath: str) -> List[Dict[str, Any]]:
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _write_json(filepath: str, data: List[Dict[str, Any]]) -> bool:
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def _ensure_user_entry(all_data: List[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
    for entry in all_data:
        if entry.get("user_id") == user_id:
            if "medications" not in entry or not isinstance(entry["medications"], list):
                entry["medications"] = []
            return entry
    entry = {"user_id": user_id, "medications": []}
    all_data.append(entry)
    return entry


def retrieve_medications(user_id: str) -> List[Dict[str, Any]]:
    data = _read_json(MEDICATION_FILE)
    for entry in data:
        if entry.get("user_id") == user_id:
            meds = entry.get("medications", [])
            return meds if isinstance(meds, list) else []
    return []


def _normalize_name(med: Dict[str, Any]) -> str:
    # Combine name + strength to reduce accidental collisions
    return f"{(med.get('drug_name') or '').strip().lower()}|{(med.get('strength') or '').strip().lower()}"


def _assign_unique_color(existing: List[Dict[str, Any]], new_norm: str) -> str:
    # Reuse color if same normalized name exists
    for m in existing:
        if _normalize_name(m) == new_norm and m.get("color"):
            return m["color"]
    used = {m.get("color") for m in existing if m.get("color")}
    for c in PALETTE:
        if c not in used:
            return c
    return PALETTE[len(existing) % len(PALETTE)]


def add_new_medication(user_id: str, new_medication: Dict[str, Any]) -> bool:
    data = _read_json(MEDICATION_FILE)
    entry = _ensure_user_entry(data, user_id)
    meds = entry["medications"]
    
    # Normalize keys for comparison
    new_name = str(new_medication.get("drug_name", "")).strip().lower()
    new_strength = str(new_medication.get("strength", "")).strip().lower()
    new_qty = int(new_medication.get("quantity_left", 0) or 0)

    # Try to find existing medication with same name + strength
    found_idx = None
    for i, m in enumerate(meds):
        if (
            str(m.get("drug_name", "")).strip().lower() == new_name
            and str(m.get("strength", "")).strip().lower() == new_strength
        ):
            found_idx = i
            break

    if found_idx is not None:
        # Renewal: increment quantity_left
        current_qty = int(meds[found_idx].get("quantity_left", 0) or 0)
        meds[found_idx]["quantity_left"] = current_qty + new_qty
    else:
        # New medication: ensure required fields and assign color
        if "dose_per_intake" not in new_medication:
            new_medication["dose_per_intake"] = 1
        if "schedule" not in new_medication:
            new_medication["schedule"] = {}
        norm = _normalize_name(new_medication)
        if not new_medication.get("color"):
            new_medication["color"] = _assign_unique_color(meds, norm)
        meds.append(new_medication)
    
    entry["medications"] = meds
    return _write_json(MEDICATION_FILE, data)


def ensure_colors(user_id: str) -> None:
    data = _read_json(MEDICATION_FILE)
    entry = _ensure_user_entry(data, user_id)
    changed = False
    for med in entry["medications"]:
        if not med.get("color"):
            norm = _normalize_name(med)
            med["color"] = _assign_unique_color(entry["medications"], norm)
            changed = True
    if changed:
        _write_json(MEDICATION_FILE, data)
