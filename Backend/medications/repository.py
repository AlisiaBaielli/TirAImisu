from typing import List
from Backend.medications.medication import Medication
import csv
import os
from typing import Optional


def _get_csv_path() -> str:
    """
    Resolve medications CSV path.
    Priority:
    - MEDICATIONS_CSV_PATH env var
    - Default: Backend/medications/medications.csv
    """
    env_path = os.getenv("MEDICATIONS_CSV_PATH")
    if env_path:
        return env_path
    return os.path.join(os.path.dirname(__file__), "medications.csv")


def get_current_medications() -> List[Medication]:
    """
    Read medications from CSV and convert to Medication instances.
    Expected headers: id,name,time,color,hour_interval,description
    """
    csv_path = _get_csv_path()
    medications: List[Medication] = []

    if not os.path.exists(csv_path):
        return medications

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue
            try:
                med = Medication(
                    id=str(row.get("id", "")).strip(),
                    name=str(row.get("name", "")).strip(),
                    time=int(str(row.get("time", "0")).strip() or 0),
                    color=str(row.get("color", "")).strip(),
                    hour_interval=int(str(row.get("hour_interval", "24")).strip() or 24),
                    description=(str(row.get("description")).strip() if row.get("description") is not None else None),
                )
                medications.append(med)
            except Exception:
                # Skip invalid rows
                continue

    return medications


def _next_id(existing: List[Medication]) -> str:
    max_id = 0
    for m in existing:
        try:
            max_id = max(max_id, int(str(m.id)))
        except Exception:
            continue
    return str(max_id + 1)


def add_medication(name: str, time: int, color: str, hour_interval: int, description: Optional[str] = None) -> Medication:
    """
    Append a new medication to the CSV and return the created Medication.
    """
    csv_path = _get_csv_path()
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    current = get_current_medications()
    new_id = _next_id(current)
    med = Medication(
        id=new_id,
        name=name,
        time=int(time),
        color=color,
        hour_interval=int(hour_interval),
        description=description,
    )

    file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    with open(csv_path, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "time", "color", "hour_interval", "description"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(med.to_dict())

    return med
