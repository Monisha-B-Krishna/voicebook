"""
Confirmation gate - simulates step 4 of the pipeline (owner confirms before
saving), using ACTUAL VOICE:
  1. Build a readback sentence
  2. Speak it out loud via Sarvam TTS
  3. Record the owner's spoken yes/no reply via mic
  4. Transcribe that reply via Sarvam ASR
  5. Keyword-match the transcribed reply (NOT a second LLM call - this
     matches the documented design: confirmation reuses ASR output but
     bypasses NLU entirely)
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))  # project root


from shared.schemas.nlu_schema import NLUResult, Transaction
from nlp.tts.tts_client import speak
from nlp.audio_io.mic_record import record_from_mic
from nlp.asr.asr_client import transcribe


def _describe_transaction(txn: Transaction) -> str:
    """Builds a plain-English readback sentence for one transaction."""
    parts = [f"{txn.intent.value}"]

    if txn.customer_name:
        parts.append(f"for {txn.customer_name}")
    if txn.item and txn.quantity:
        parts.append(f"- {txn.quantity} {txn.item}")
    elif txn.item:
        parts.append(f"- {txn.item}")
    elif txn.quantity:
        parts.append(f"- quantity {txn.quantity}")
    if txn.amount:
        label = txn.payment_type or "amount"
        parts.append(f"- ₹{txn.amount:.0f} ({label})")
    if txn.date:
        parts.append(f"- date {txn.date}")

    return " ".join(parts)


# Keyword sets for confirm/reject - lightweight matching on the ASR
# transcript of the owner's spoken reply, no LLM call involved.
# Includes both Latin transliteration AND actual Kannada script, since
# Sarvam's ASR transcribes spoken Kannada words into Kannada script, not
# Latin letters - matching only "haudu" would miss "ಹೌದು" entirely.
#
# NOTE: "ಆಗಿದೆ" (has happened/is done) was removed from this list - it's a
# common word that shows up in ordinary correction sentences too (e.g.
# "50 chair 30 chair add ಆಗಿದೆ" = "50+30 chairs got added" - a correction,
# NOT a yes), so it was causing false-positive confirmations of wrong data.
CONFIRM_WORDS = {
    "yes", "y", "confirm", "ok", "correct",
    "haudu", "houdu", "sari",
    "ಹೌದು", "ಸರಿ", "ಹ್ಮ್",
}
REJECT_WORDS = {
    "no", "n", "cancel", "wrong",
    "beda", "illa", "tappu",
    "ಬೇಡ", "ಇಲ್ಲ", "ತಪ್ಪು",
}

# A genuine yes/no reply is short. If the owner's reply is long AND contains
# numbers, they are almost certainly explaining a correction, not simply
# confirming or rejecting - even if a confirm/reject word happens to appear
# somewhere in it. In that case we should NOT auto-confirm OR auto-reject;
# we flag it as unclear so the flow asks again rather than silently
# misinterpreting a correction as approval.
MAX_SIMPLE_REPLY_WORDS = 6


def confirm_with_owner(result: NLUResult) -> bool:
    """
    Speaks the readback aloud, records the owner's spoken reply, transcribes
    it, and keyword-matches to decide confirm/reject.
    """
    print("\n--- Readback for confirmation ---")
    readback_lines = []
    for i, txn in enumerate(result.transactions, 1):
        line = _describe_transaction(txn)
        print(f"{i}. {line}")
        readback_lines.append(line)
    print("----------------------------------")

    readback_text = ". ".join(readback_lines) + ". Correct-a?"
    speak(readback_text)

    reply_audio_path = record_from_mic(
        "confirm_reply",
        prompt="Press ENTER to START speaking your yes/no reply...",
    )
    reply_transcript = transcribe(reply_audio_path)
    print(f"Heard: {reply_transcript}")

    reply_lower = reply_transcript.strip().lower()
    word_count = len(reply_transcript.strip().split())
    has_digits = any(char.isdigit() for char in reply_transcript)

    # Safeguard: a long reply with numbers in it is almost certainly a
    # correction being explained, not a simple yes/no - don't let a single
    # matching word (from either list) override that.
    if word_count > MAX_SIMPLE_REPLY_WORDS and has_digits:
        print(
            "This sounds like a correction, not a simple yes/no. "
            "Treating as 'no' so nothing wrong gets saved - please re-record "
            "the booking with the correct details."
        )
        return False

    if any(word in reply_lower for word in CONFIRM_WORDS):
        return True
    elif any(word in reply_lower for word in REJECT_WORDS):
        return False
    else:
        print("Didn't recognize a clear yes/no in that reply, treating as 'no' - please retry.")
        return False