"""
TTS client: sends text to Sarvam's Bulbul TTS API, saves the audio, and
plays it back through your speakers - so the confirmation readback is
actually SPOKEN, not printed.

SETUP:
Uses the same SARVAM_API_KEY from your .env file.
pip install requests python-dotenv

NOTE: winsound (used for playback) only works on Windows and only plays
WAV files. If Sarvam returns a different format, we may need to convert -
tell me what happens when you test this.
"""

import os
import base64
import winsound
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TTS_OUTPUT_FOLDER = PROJECT_ROOT / "data" / "audio" / "tts_output"


def _call_sarvam_tts(text: str, language_code: str = "kn-IN") -> bytes:
    """
    Shared core: calls Sarvam TTS and returns raw decoded audio bytes.
    Used by both speak() (local playback, for the desktop demo) and
    synthesize_audio_bytes() (server-side, for the mobile app - the
    server generates the bytes, the PHONE plays them, not the server).
    """
    if not SARVAM_API_KEY:
        raise ValueError("SARVAM_API_KEY not found in .env file")

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "target_language_code": language_code,
        "model": "bulbul:v3",
    }

    response = requests.post(SARVAM_TTS_URL, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()

    audio_b64_list = result.get("audios")
    if not audio_b64_list:
        raise ValueError(f"Unexpected TTS response shape. Keys: {list(result.keys())}")

    return base64.b64decode(audio_b64_list[0])


def synthesize_audio_bytes(text: str, language_code: str = "kn-IN") -> bytes:
    """
    Server-side TTS: returns raw WAV audio bytes for the caller (e.g. a
    FastAPI endpoint) to send to the mobile app, which plays them via
    AudioService.playBytes(). No local file writing, no winsound - this
    runs on the backend server, not the desktop demo machine.
    """
    return _call_sarvam_tts(text, language_code)


def speak(text: str, language_code: str = "kn-IN"):
    """
    Converts text to speech via Sarvam TTS, saves into data/audio/tts_output/
    with a timestamped filename, and plays it immediately. This is for the
    LOCAL desktop demo pipeline (full_demo_pipeline.py) - Windows-only due
    to winsound.
    """
    TTS_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = TTS_OUTPUT_FOLDER / f"tts_output_{timestamp}.wav"

    audio_bytes = _call_sarvam_tts(text, language_code)

    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    print(f"Playing TTS audio: {text}")
    winsound.PlaySound(str(output_path), winsound.SND_FILENAME)
    return str(output_path)


if __name__ == "__main__":
    speak("Raju gagi hadinaidu chair booking aagide", language_code="kn-IN")
