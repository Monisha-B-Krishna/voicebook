"""
General-purpose TTS endpoint: converts any text to spoken Kannada audio
bytes. Used for reading back booking/payment/return confirmations aloud
before the owner confirms - not just query answers (balance/orders).
"""

import sys
import base64
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))  # project root

from fastapi import APIRouter
from pydantic import BaseModel

from nlp.tts.tts_client import synthesize_audio_bytes


router = APIRouter(
    prefix="/tts",
    tags=["Text to Speech"]
)


class SynthesizeRequest(BaseModel):
    text: str
    language_code: str = "kn-IN"


@router.post("/synthesize")
def synthesize(request: SynthesizeRequest):
    try:
        audio_bytes = synthesize_audio_bytes(request.text, request.language_code)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        return {"status": "success", "audio_base64": audio_base64}
    except Exception as e:
        return {"status": "error", "message": str(e)}
