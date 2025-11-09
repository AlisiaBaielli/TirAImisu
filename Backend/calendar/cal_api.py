import requests
from datetime import datetime
import pytz  # pip install pytz
import os
from dotenv import load_dotenv

# Load variables from a local .env file if present
load_dotenv()

API_TOKEN = os.getenv("CAL_API_TOKEN")
BASE_URL = os.getenv("CAL_API_BASE_URL")
TIMEZONE = os.getenv("TIMEZONE") or "UTC"

# Validate and normalize required environment variables early to fail fast
if not BASE_URL:
    raise RuntimeError(
        "Missing CAL_API_BASE_URL. Set it in your environment or .env (e.g., https://api.calapi.io)."
    )
if not (BASE_URL.startswith("http://") or BASE_URL.startswith("https://")):
    raise RuntimeError(
        f"CAL_API_BASE_URL must include http(s) scheme, got: '{BASE_URL}'. Example: https://api.calapi.io"
    )
BASE_URL = BASE_URL.rstrip("/")

if not API_TOKEN:
    raise RuntimeError("Missing CAL_API_TOKEN. Set it in your environment or .env.")

HEADERS = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}


def list_events(calendar_id="cal_OODZTUtc1Y"):
    """List all events in a calendar."""
    url = f"{BASE_URL}/calendars/{calendar_id}/events"
    response = requests.get(url, headers=HEADERS)
    if response.ok:
        return response.json()["data"]
    else:
        print(f"Error listing events: {response.status_code} {response.text}")
        return []


def create_event(calendar_id, title, start_dt, end_dt, description=None, location=None):
    """Create a new event with timezone-aware datetimes."""
    tz = pytz.timezone(TIMEZONE)
    start_time = tz.localize(start_dt)
    end_time = tz.localize(end_dt)

    payload = {
        "title": title,
        "description": description,
        "location": location,
        "start": {"date_time": start_time.isoformat()},
        "end": {"date_time": end_time.isoformat()},
    }

    url = f"{BASE_URL}/calendars/{calendar_id}/events"
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.ok:
        return response.json()["data"]
    else:
        print(f"Error creating event: {response.status_code} {response.text}")
        return None


def retrieve_event(calendar_id, event_id):
    """Retrieve details of a specific event."""
    url = f"{BASE_URL}/calendars/{calendar_id}/events/{event_id}"
    response = requests.get(url, headers=HEADERS)
    if response.ok:
        return response.json()["data"]
    else:
        print(f"Error retrieving event: {response.status_code} {response.text}")
        return None


def update_event(
    calendar_id,
    event_id,
    title=None,
    start_dt=None,
    end_dt=None,
    description=None,
    location=None,
):
    """Update an existing event. Provide only the fields you want to change."""
    payload = {}
    tz = pytz.timezone(TIMEZONE)

    if title:
        payload["title"] = title
    if description:
        payload["description"] = description
    if location:
        payload["location"] = location
    if start_dt:
        payload["start"] = {"date_time": tz.localize(start_dt).isoformat()}
    if end_dt:
        payload["end"] = {"date_time": tz.localize(end_dt).isoformat()}

    url = f"{BASE_URL}/calendars/{calendar_id}/events/{event_id}"
    response = requests.patch(url, json=payload, headers=HEADERS)
    if response.ok:
        return response.json()["data"]
    else:
        print(f"Error updating event: {response.status_code} {response.text}")
        return None


def delete_event(calendar_id, event_id):
    """Delete an event."""
    url = f"{BASE_URL}/calendars/{calendar_id}/events/{event_id}"
    response = requests.delete(url, headers=HEADERS)
    if response.ok:
        print(f"Event {event_id} deleted successfully.")
    else:
        print(f"Error deleting event: {response.status_code} {response.text}")
