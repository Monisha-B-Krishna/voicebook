
"""
TTS client: sends text to Sarvam Bulbul TTS API, saves audio,
and plays it locally on Windows.

Mobile/backend use:
    synthesize_audio_bytes() returns audio bytes to FastAPI.
    The phone plays the audio; the server does not need speakers.

Local desktop use:
    speak() saves a WAV file and plays it using Windows winsound.
"""

import os
import base64
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

try:
    import winsound
except ImportError:
    winsound = None


load_dotenv()

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TTS_OUTPUT_FOLDER = PROJECT_ROOT / "data" / "audio" / "tts_output"


def _call_sarvam_tts(text: str, language_code: str = "kn-IN") -> bytes:
    """
    Calls Sarvam TTS and returns decoded audio bytes.
    """

    if not SARVAM_API_KEY:
        raise ValueError("SARVAM_API_KEY not found in environment or .env file")

    if not text or not text.strip():
        raise ValueError("TTS text cannot be empty")

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "target_language_code": language_code,
        "model": "bulbul:v3",
    }

    response = requests.post(
        SARVAM_TTS_URL,
        headers=headers,
        json=payload,
        timeout=60,
    )

    response.raise_for_status()

    result = response.json()

    audio_b64_list = result.get("audios")

    if not audio_b64_list:
        raise ValueError(
            f"Unexpected TTS response shape. Keys: {list(result.keys())}"
        )

    return base64.b64decode(audio_b64_list[0])


def synthesize_audio_bytes(
    text: str,
    language_code: str = "kn-IN",
) -> bytes:
    """
    Server-side TTS.

    Returns audio bytes to the FastAPI endpoint.
    No local playback or winsound dependency.
    """

    return _call_sarvam_tts(text, language_code)


def speak(
    text: str,
    language_code: str = "kn-IN",
):
    """
    Local desktop TTS.

    Saves the generated audio and plays it on Windows.
    """

    if winsound is None:
        raise RuntimeError(
            "Local audio playback is only available on Windows."
        )

    TTS_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_path = (
        TTS_OUTPUT_FOLDER / f"tts_output_{timestamp}.wav"
    )

    audio_bytes = _call_sarvam_tts(text, language_code)

    with open(output_path, "wb") as audio_file:
        audio_file.write(audio_bytes)

    print(f"Playing TTS audio: {text}")

    winsound.PlaySound(
        str(output_path),
        winsound.SND_FILENAME,
    )

    return str(output_path)


if __name__ == "__main__":
    speak(
        "Raju gagi hadinaidu chair booking aagide",
        language_code="kn-IN",
    )
