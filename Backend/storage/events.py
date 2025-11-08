import json
import os
import tempfile
from typing import Any, Dict, List

DEFAULT_CACHE_PATH = os.getenv(
    "EVENTS_CACHE_PATH",
    os.path.join(os.path.dirname(__file__), "events_cache.json"),
)


def _ensure_dir(path: str) -> None:
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def _load_cache(cache_path: str = DEFAULT_CACHE_PATH) -> Dict[str, List[Dict[str, Any]]]:
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        # Corrupt or unreadable cache -> treat as empty
        return {}


def _save_cache(data: Dict[str, List[Dict[str, Any]]], cache_path: str = DEFAULT_CACHE_PATH) -> None:
    _ensure_dir(cache_path)
    # Atomic write
    fd, tmp_path = tempfile.mkstemp(prefix="events_cache_", suffix=".json", dir=os.path.dirname(cache_path) or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, cache_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def get_events(calendar_id: str, cache_path: str = DEFAULT_CACHE_PATH) -> List[Dict[str, Any]]:
    cache = _load_cache(cache_path)
    return cache.get(calendar_id, [])


def set_events(calendar_id: str, events: List[Dict[str, Any]], cache_path: str = DEFAULT_CACHE_PATH) -> None:
    cache = _load_cache(cache_path)
    cache[calendar_id] = events
    _save_cache(cache, cache_path)


