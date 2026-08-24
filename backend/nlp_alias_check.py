"""
Alias check step: runs BEFORE sending a confirmed transaction to the
backend. For each customer_name in the transaction, asks the backend if
there's a similar-sounding existing customer. If so, asks the OWNER by
voice to confirm whether it's the same person - never auto-merges.

This file belongs conceptually with the nlp/demo/ pipeline scripts, but
is delivered separately since it depends on both the NLP audio/TTS
modules AND the backend's /customers/similar endpoint being reachable.

Usage: call check_and_resolve_aliases(nlu_result_dict) before
send_to_backend.py's send_transaction() call.
"""

import sys
from pathlib import Path
import requests

sys.path.append(str(Path(__file__).resolve().parents[1]))  # project root

from nlp.tts.tts_client import speak
from nlp.audio_io.mic_record import record_from_mic
from nlp.asr.asr_client import transcribe

CONFIRM_WORDS = {"yes", "y", "haudu", "houdu", "sari", "ಹೌದು", "ಸರಿ", "ಹ್ಮ್"}


def check_and_resolve_aliases(nlu_result_dict: dict, base_url: str = "http://localhost:8000"):
    """
    Mutates nothing in nlu_result_dict - just creates alias records in the
    backend BEFORE the main transaction is sent, so find_or_create_customer
    picks up the alias when the real transaction is processed.
    """
    seen_names = set()

    for txn in nlu_result_dict.get("transactions", []):
        name = txn.get("customer_name")
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        response = requests.get(f"{base_url}/customers/similar", params={"name": name})
        if response.status_code != 200:
            continue

        matches = response.json()
        if not matches:
            continue

        # Only ask about the single closest match to avoid a long back-and-forth
        best_match = matches[0]
        question = (
            f"Is {name} the same person as your existing customer "
            f"{best_match['name']}? Say yes or no."
        )
        print(f"\n[Alias check] {question}")
        speak(question)

        reply_path = record_from_mic(
            "alias_confirm",
            prompt="Press ENTER to START speaking your yes/no reply...",
        )
        reply_transcript = transcribe(reply_path)
        print(f"Heard: {reply_transcript}")

        if any(word in reply_transcript.lower() for word in CONFIRM_WORDS):
            alias_response = requests.post(
                f"{base_url}/customers/{best_match['customer_id']}/aliases",
                json={"alias_name": name},
            )
            print(f"Alias recorded: '{name}' -> customer_id {best_match['customer_id']}")
        else:
            print(f"Not the same person - '{name}' will be created as a new customer.")
