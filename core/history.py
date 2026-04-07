# core/history.py
"""
History management for the rota solver.

Handles:
- Loading/Saving history.json
- Appending each month's assignment
- Providing structure for fairness weighting

Expected JSON structure:

{
    "months": [
        {
            "timestamp": "2026-03-01",
            "assignment": {
                "Person A": "Area X",
                "Person B": "Area Y",
                ...
            }
        },
        ...
    ]
}
"""

import json
import datetime
import os


# ------------------------------------------------------------
# LOADING + SAVING
# ------------------------------------------------------------

def load_history(path="data/history.json"):
    """Load rotation history from JSON. Create empty if missing."""
    if not os.path.exists(path):
        return {"months": []}

    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        # If file corrupt, reset history
        return {"months": []}


def save_history(history, path="data/history.json"):
    """Save rotation history JSON."""
    with open(path, "w") as f:
        json.dump(history, f, indent=4)
def clear_history(path="data/history.json"):
    with open(path, "w") as f:
        f.write('{"months": []}')

# ------------------------------------------------------------
# UPDATING HISTORY
# ------------------------------------------------------------

def update_history(history, assignment, people, areas):
    """
    Sick people have assignment = None.
    We store them as "Sick" in history.
    """
    mapping = {}
    for i in range(len(people)):
        person = people[i]
        area_idx = assignment[i]

        if area_idx is None:
            mapping[person] = "Sick"
        else:
            mapping[person] = areas[area_idx]

    month_entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "assignment": mapping
    }
    history["months"].append(month_entry)
