"""
ASR client: sends a WAV audio file to Sarvam AI's Speech-to-Text API
(saaras model, Codemix mode) and returns the transcript.

SETUP:
Add to your .env file:  SARVAM_API_KEY=your_key_here
pip install requests python-dotenv

Run standalone to test: python asr_client.py path/to/audio.wav
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")


def transcribe(audio_path: str, language_code: str = "kn-IN", mode: str = "codemix") -> str:
    """
    Sends an audio file to Sarvam ASR and returns the transcript text.
    mode: "codemix" keeps English words in Latin script, Kannada in Kannada script.
    """
    if not SARVAM_API_KEY:
        raise ValueError("SARVAM_API_KEY not found in .env file")

    headers = {"api-subscription-key": SARVAM_API_KEY}

    with open(audio_path, "rb") as f:
        files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
        data = {
            "model": "saaras:v3",
            "language_code": language_code,
            "mode": mode,
        }
        response = requests.post(SARVAM_API_URL, headers=headers, files=files, data=data)

    response.raise_for_status()
    result = response.json()

    # Sarvam's response shape - adjust key name here if their API differs
    transcript = result.get("transcript", "")
    return transcript


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python asr_client.py path/to/audio.wav")
        sys.exit(1)

    audio_file = sys.argv[1]
    print(f"Transcribing {audio_file}...")
    text = transcribe(audio_file)
    print(f"\nTranscript:\n{text}")
