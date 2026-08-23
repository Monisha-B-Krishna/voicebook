"""
Full VoiceBook pipeline demo (local, NLP-layer focused):

  Voice input -> ASR -> NLU -> Confirm with owner -> Save JSON

This is a TEST SCAFFOLD for your NLP layer (ASR + NLU), not the production
system. The real production pipeline has:
  - Flutter app for voice input + TTS confirmation (Kiruba's frontend)
  - FastAPI + PostgreSQL for business logic + staging + permanent storage
    (Kiruba's backend, Layer 4 in the SRS)

This script simulates those missing pieces just enough to test your ASR+NLU
work end-to-end, exactly as it will be used in the real system:
  1. Record or point to an audio file (stand-in for the Flutter app)
  2. Transcribe via Sarvam ASR
  3. Extract structured data via NLU (Claude/Groq/Ollama)
  4. Read back and get typed y/n confirmation (stand-in for TTS + voice reply)
  5. If confirmed, save to local JSON (stand-in for the staging + DB write)

Usage:
  python full_demo_pipeline.py path/to/audio.wav
  python full_demo_pipeline.py path/to/audio.wav --backend groq
  python full_demo_pipeline.py --text "Raju ge fifteen chairs kottidaare"
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))  # project root


import argparse

from nlp.asr.asr_client import transcribe
from nlp.nlu.nlu_client import parse_utterance
from nlp.demo.confirm import confirm_with_owner
from nlp.demo.storage import save_transaction
from nlp.audio_io.mic_record import record_from_mic


MAX_ATTEMPTS = 3


def run(audio_path: str = None, text: str = None, backend: str = None, live: bool = False):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt > 1:
            print(f"\n=== Retry attempt {attempt} of {MAX_ATTEMPTS} ===")
            print("Let's try again - please re-record the booking.\n")

        # Step 1 + 2: Voice input -> ASR
        if text:
            transcript = text
            print(f"[Step 1-2] Using typed text directly (skipping ASR):\n{transcript}\n")
        elif live:
            print("[Step 1] Recording your booking/payment/return/query by voice...")
            audio_path_used = record_from_mic("live_input", prompt="Press ENTER to START speaking...")
            print(f"[Step 2] Transcribing via Sarvam ASR...")
            transcript = transcribe(audio_path_used)
            print(f"Transcript:\n{transcript}\n")
        else:
            print(f"[Step 1-2] Transcribing {audio_path} via Sarvam ASR...")
            transcript = transcribe(audio_path)
            print(f"Transcript:\n{transcript}\n")

        # Step 3: NLU
        print(f"[Step 3] Sending to NLU (backend: {backend or 'default'})...")
        result = parse_utterance(transcript, backend=backend)
        print("Parsed result:")
        print(result.model_dump_json(indent=2))

        # Step 4: Confirmation
        confirmed = confirm_with_owner(result)

        # Step 5: Save (only if confirmed)
        if confirmed:
            saved_entry = save_transaction(result.model_dump())
            print(f"\n[Step 5] Saved to data/transactions.json")
            return saved_entry
        else:
            print("\n[Step 5] NOT saved - owner rejected the readback.")
            if text:
                # typed text mode can't meaningfully "re-record" - stop here
                print("(Using --text mode, can't re-record. Try a different --text value.)")
                return None
            if attempt == MAX_ATTEMPTS:
                print(f"Reached max attempts ({MAX_ATTEMPTS}). Stopping - please try running the command again.")
                return None
            # otherwise, loop continues and re-records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VoiceBook full pipeline demo")
    parser.add_argument("audio", nargs="?", help="Path to a WAV audio file")
    parser.add_argument("--text", help="Skip ASR, use this typed text instead")
    parser.add_argument("--live", action="store_true", help="Record live from your mic instead of using a file")
    parser.add_argument("--backend", choices=["claude", "groq", "ollama"], help="NLU backend to use")
    args = parser.parse_args()

    if not args.audio and not args.text and not args.live:
        parser.error("Provide an audio file path, --text, or --live")

    run(audio_path=args.audio, text=args.text, backend=args.backend, live=args.live)