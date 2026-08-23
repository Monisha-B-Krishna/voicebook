"""
Local storage for confirmed transactions - simulates the "save to database"
step for demo/testing purposes. In the real system, this is Kiruba's
PostgreSQL staging table + FastAPI backend (Layer 4 in the SRS).

For now: appends confirmed transactions to a local JSON file, so you have
something to query later (e.g. testing QUERY intent against real saved data).
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Resolve project root regardless of where this script is called from
PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORAGE_FILE = PROJECT_ROOT / "data" / "transactions.json"


def _ensure_storage_exists():
    STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STORAGE_FILE.exists():
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def save_transaction(nlu_result_dict: dict):
    """
    Appends a confirmed NLUResult (as a dict) to the local JSON store.
    Each entry gets a saved_at timestamp separate from entry_timestamp -
    entry_timestamp is when the owner SPOKE it, saved_at is when it was
    actually confirmed and written to storage (these can differ if the
    owner takes a moment to confirm, or if confirmation fails and retries).
    """
    _ensure_storage_exists()

    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    entry = {
        "saved_at": datetime.now().isoformat(),
        **nlu_result_dict,
    }
    records.append(entry)

    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    return entry


def load_all_transactions() -> list:
    _ensure_storage_exists()
    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    records = load_all_transactions()
    print(f"{len(records)} saved transaction(s) in {STORAGE_FILE}")
    for r in records:
        print(json.dumps(r, indent=2, ensure_ascii=False))
