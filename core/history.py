import os
import json

HISTORY_DIR = "data"
HISTORY_PATH = os.path.join(HISTORY_DIR, "history.json")


def ensure_history_dir():
    """Ensure the data folder exists and is writable."""
    try:
        os.makedirs(HISTORY_DIR, exist_ok=True)
    except Exception:
        pass


def load_history():
    ensure_history_dir()

    if not os.path.exists(HISTORY_PATH):
        return {"months": []}

    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"months": []}


def save_history(history):
    ensure_history_dir()

    tmp_path = HISTORY_PATH + ".tmp"

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
        os.replace(tmp_path, HISTORY_PATH)
    except PermissionError:
        # OneDrive or Docker bind can lock the file — fallback to memory only
        pass


def update_history(history, assignment, people, areas):
    month_record = {
        "assignment": {people[i]: (areas[a] if a is not None else "Sick") for i, a in enumerate(assignment)}
    }
    history.setdefault("months", []).append(month_record)


def clear_history():
    ensure_history_dir()

    try:
        if os.path.exists(HISTORY_PATH):
            os.remove(HISTORY_PATH)
    except PermissionError:
        # File is locked (OneDrive), so overwrite instead
        try:
            with open(HISTORY_PATH, "w", encoding="utf-8") as f:
                f.write('{"months": []}')
        except Exception:
            pass