"""
Sends a confirmed NLUResult to the backend's /voice-transactions endpoint.
This replaces the local storage.py save step for real end-to-end testing
against Kiruba's actual database, instead of just saving to a local JSON
file.

Run the backend first (docker-compose up, then uvicorn app.main:app),
then run this against a saved transaction or a live pipeline run.

Usage:
  python send_to_backend.py                          # sends the last
                                                       # saved local transaction
  python send_to_backend.py --url http://localhost:8000
"""

import sys
import json
import argparse
import requests
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # project root


def send_transaction(nlu_result_dict: dict, base_url: str = "http://localhost:8000"):
    response = requests.post(
        f"{base_url}/voice-transactions/",
        json=nlu_result_dict,
    )
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()

    # Load the most recent locally-saved transaction to send as a test
    transactions_file = Path(__file__).resolve().parents[1] / "data" / "transactions.json"
    with open(transactions_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        print("No local transactions found in data/transactions.json - run the NLP pipeline first.")
        sys.exit(1)

    latest = records[-1]
    print(f"Sending most recent transaction: {latest['raw_transcript']}\n")
    send_transaction(latest, base_url=args.url)
