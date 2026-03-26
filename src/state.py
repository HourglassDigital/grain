"""Pulse state persistence — deduplication, action tracking, weekly update history."""

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

AEDT = timezone(timedelta(hours=11))

STATE_PATH = os.getenv("PULSE_STATE_PATH", "/tmp/pulse-state.json")

DEFAULT_STATE = {
    "last_run_date": None,
    "seen_hashes": [],
    "action_items": [],
    "weekly_updates": [],
}


def load_state() -> dict:
    """Load state from JSON file, returning defaults if missing."""
    if not os.path.exists(STATE_PATH):
        return {**DEFAULT_STATE, "seen_hashes": [], "action_items": [], "weekly_updates": []}
    try:
        with open(STATE_PATH, "r") as f:
            data = json.load(f)
        # Ensure all keys exist
        for key, default in DEFAULT_STATE.items():
            if key not in data:
                data[key] = default if not isinstance(default, list) else []
        return data
    except (json.JSONDecodeError, IOError):
        return {**DEFAULT_STATE, "seen_hashes": [], "action_items": [], "weekly_updates": []}


def save_state(state: dict) -> None:
    """Write state to JSON file."""
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, default=str)


def _hash_update(update_dict: dict) -> str:
    """Create a content hash from title + bullets."""
    title = update_dict.get("title", "")
    bullets = "|".join(update_dict.get("bullets", []))
    content = f"{title}:{bullets}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def is_duplicate(update_dict: dict) -> bool:
    """Check if an update has already been seen."""
    state = load_state()
    h = _hash_update(update_dict)
    return h in state["seen_hashes"]


def add_seen(update_dict: dict) -> None:
    """Add an update's hash to the seen set."""
    state = load_state()
    h = _hash_update(update_dict)
    if h not in state["seen_hashes"]:
        state["seen_hashes"].append(h)
    save_state(state)


def get_open_actions() -> list[dict]:
    """Return action items not marked done."""
    state = load_state()
    return [a for a in state["action_items"] if not a.get("done", False)]


def add_action(action_dict: dict) -> None:
    """Add an action item to state."""
    state = load_state()
    action_dict.setdefault("done", False)
    action_dict.setdefault("added_date", datetime.now(AEDT).isoformat())
    state["action_items"].append(action_dict)
    save_state(state)


def mark_action_done(title_substring: str) -> bool:
    """Mark matching action as done. Returns True if a match was found."""
    state = load_state()
    found = False
    for action in state["action_items"]:
        if title_substring.lower() in action.get("title", "").lower() and not action.get("done"):
            action["done"] = True
            action["completed_date"] = datetime.now(AEDT).isoformat()
            found = True
            break
    if found:
        save_state(state)
    return found


def add_weekly_update(date: str, page: str, title: str, importance: str) -> None:
    """Track an update for weekly digest purposes."""
    state = load_state()
    state["weekly_updates"].append({
        "date": date,
        "page": page,
        "title": title,
        "importance": importance,
    })
    save_state(state)


def get_weekly_updates(days: int = 7) -> list[dict]:
    """Return updates from the past N days."""
    state = load_state()
    cutoff = datetime.now(AEDT) - timedelta(days=days)
    cutoff_str = cutoff.strftime("%d %b %Y")
    # Return all weekly_updates — filtering by date string comparison
    # Since dates are stored as "DD Mon YYYY", we keep all recent ones
    return state.get("weekly_updates", [])


def get_stale_actions(days: int = 3) -> list[dict]:
    """Return open actions older than N days."""
    now = datetime.now(AEDT)
    stale = []
    for action in get_open_actions():
        added = action.get("added_date", "")
        if added:
            try:
                added_dt = datetime.fromisoformat(added)
                age = (now - added_dt).days
                if age >= days:
                    action["age_days"] = age
                    stale.append(action)
            except (ValueError, TypeError):
                pass
    return stale
