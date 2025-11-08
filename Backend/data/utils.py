import json
import os
import shutil
from typing import List, Dict, Any

# Get the absolute path of the directory this script (utils.py) is in
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define file paths
MEDICATION_FILE = os.path.join(SCRIPT_DIR, 'personal_medication.json')
USER_DATA_FILE = os.path.join(SCRIPT_DIR, 'personal_data.json')

def _read_json(filepath: str) -> List[Dict[str, Any]]:
    if not os.path.exists(filepath):
        return []  # Return an empty list if the file doesn't exist
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        print(f"Warning: '{filepath}' contains invalid JSON. Returning an empty list.")
        return []


def _write_to_json(filepath: str, data: List[Dict[str, Any]]) -> bool:
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except IOError as e:
        print(f"Error: Could not write to file '{filepath}'. {e}")
        return False
    except TypeError as e:
        print(f"Error: Data provided is not JSON serializable. {e}")
        return False


def retrieve_medications(user_id: str) -> List[Dict[str, Any]]:
    all_med_data = _read_json(MEDICATION_FILE)
    print("All med data: ", all_med_data)

    for user_data in all_med_data:
        if user_data.get("user_id") == user_id:
            return user_data.get("medications", [])

    return []


def add_new_medication(user_id: str, new_medication: Dict[str, Any]) -> bool:
    all_med_data = _read_json(MEDICATION_FILE)

    for user_data in all_med_data:
        if user_data.get("user_id") == user_id:
            if "medications" not in user_data or not isinstance(
                user_data.get("medications"), list
            ):
                user_data["medications"] = []
            user_data["medications"].append(new_medication)

    return _write_to_json(MEDICATION_FILE, all_med_data)