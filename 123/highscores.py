"""
Persistent high scores, saved to a local JSON file next to this project.
"""

import json
import os

from settings import MAX_HIGH_SCORES

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HIGH_SCORE_FILE = os.path.join(SCRIPT_DIR, "zombie_shooter_highscores.json")


def load_high_scores():
    if not os.path.exists(HIGH_SCORE_FILE):
        return []
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_high_scores(scores):
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            json.dump(scores, f, indent=2)
    except OSError:
        pass


def update_high_scores(scores, score, level):
    new_entry = {"score": score, "level": level}
    updated = scores + [new_entry]
    updated.sort(key=lambda e: e["score"], reverse=True)
    updated = updated[:MAX_HIGH_SCORES]
    is_new_record = new_entry in updated and (
        len(scores) < MAX_HIGH_SCORES or score > scores[-1]["score"]
    )
    save_high_scores(updated)
    return updated, is_new_record
