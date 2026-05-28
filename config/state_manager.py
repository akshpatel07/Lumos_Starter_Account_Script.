# ─────────────────────────────────────────────────────────────
#  config/state_manager.py  —  Persistent run-counter for D-codes
#
#  The counter is stored in  state.json  at the project root.
#  Format:  { "run_number": 1 }
#
#  D-code is zero-padded to at least 3 digits:
#    run 1  → D001
#    run 10 → D010
#    run 100→ D100
# ─────────────────────────────────────────────────────────────

import json
import os

# ── Path to the state file (project root, next to main.py) ───
_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "state.json",
)

_DEFAULT_STATE = {"run_number": 1}


def _load_state() -> dict:
    """Read state.json; return defaults if file is missing or corrupt."""
    if not os.path.exists(_STATE_FILE):
        return dict(_DEFAULT_STATE)
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "run_number" not in data:
            data["run_number"] = 1
        return data
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT_STATE)


def _save_state(state: dict) -> None:
    """Write state.json atomically."""
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_current_code() -> str:
    """
    Return the D-code for the *current* run without incrementing.
    E.g. 'D001', 'D010', 'D100'.
    """
    state = _load_state()
    n = state["run_number"]
    # Always at least 3 digits; grows naturally beyond that
    width = max(3, len(str(n)))
    return f"D{str(n).zfill(width)}"


def increment_code() -> str:
    """
    Increment the counter by 1 and save.
    Returns the *new* code that will be used on the NEXT run.
    Call this after a successful (or even failed) run.
    """
    state = _load_state()
    state["run_number"] += 1
    _save_state(state)
    n = state["run_number"]
    width = max(3, len(str(n)))
    next_code = f"D{str(n).zfill(width)}"
    print(f"[*] Run counter incremented → next run will use code: {next_code}")
    return next_code
