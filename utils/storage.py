import json
import os
from typing import Any, Dict

VOICE_TIMES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "voice_times.json")


def _ensure_voice_file() -> None:
    if not os.path.exists(VOICE_TIMES_FILE):
        default = {"times": {}, "active": {}}
        try:
            with open(VOICE_TIMES_FILE, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def load_voice_data() -> Dict[str, Any]:
    _ensure_voice_file()
    try:
        with open(VOICE_TIMES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"times": {}, "active": {}}

    # Normalize structure
    if not isinstance(data, dict):
        data = {}
    data.setdefault("times", {})
    data.setdefault("active", {})
    return data


def save_voice_data(data: Dict[str, Any]) -> None:
    try:
        with open(VOICE_TIMES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# Backwards-compatible stubs (if other modules import these)
def load_game_data() -> Dict[str, Any]:
    return {"balances": {}, "last_used": {}}


def save_game_data(data: Dict[str, Any]) -> None:
    return
