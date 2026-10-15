"""
Full VoiceBook NLU pipeline: audio file -> Sarvam ASR -> NLU -> validated JSON.

Usage:
  python run_pipeline.py path/to/audio.wav
  python run_pipeline.py path/to/audio.wav --backend groq
  python run_pipeline.py path/to/audio.wav --backend claude
  python run_pipeline.py path/to/audio.wav --backend ollama   (default)

Or test with typed text directly (skips ASR):
  python run_pipeline.py --text "Raju ge fifteen chairs kottidaare"
"""

import sys
import argparse

from asr_client import transcribe
from nlu_client import parse_utterance


def run(audio_path: str = None, text: str = None, backend: str = None):
    if text:
        transcript = text
        print(f"Using typed text directly (skipping ASR):\n{transcript}\n")
    else:
        print(f"Step 1: Transcribing {audio_path} via Sarvam ASR...")
        transcript = transcribe(audio_path)
        print(f"Transcript:\n{transcript}\n")

    print(f"Step 2: Sending to NLU (backend: {backend or 'default'})...")
    result = parse_utterance(transcript, backend=backend)

    print("\nFinal structured output:")
    print(result.model_dump_json(indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VoiceBook NLU pipeline")
    parser.add_argument("audio", nargs="?", help="Path to a WAV audio file")
    parser.add_argument("--text", help="Skip ASR, use this typed text instead")
    parser.add_argument("--backend", choices=["claude", "groq", "ollama"], help="NLU backend to use")
    args = parser.parse_args()

    if not args.audio and not args.text:
        parser.error("Provide either an audio file path or --text")

    run(audio_path=args.audio, text=args.text, backend=args.backend)
