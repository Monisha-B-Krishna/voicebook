"""
Audio intake endpoint for the mobile app: accepts a recorded audio file
from the Flutter app, runs it through the existing ASR + NLU pipeline
(reusing nlp/asr/asr_client.py and nlp/nlu/nlu_client.py directly - no
duplicated logic), and returns the parsed NLUResult JSON for the app to
display and let the owner confirm/edit.

IMPORTANT: this endpoint does NOT save anything to the database. It only
parses. The app calls /voice-transactions/ separately, after the owner
confirms on screen, to actually save - keeping "understand what was said"
and "commit it to the database" as two distinct, separately-testable steps.
"""

import sys
import tempfile
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))  # project root

from fastapi import APIRouter, UploadFile, File, Query

from nlp.asr.asr_client import transcribe
from nlp.nlu.nlu_client import parse_utterance


router = APIRouter(
    prefix="/voice",
    tags=["Voice Audio Intake"]
)


@router.post("/process-audio")
async def process_audio(
    file: UploadFile = File(...),
    backend: str = Query(default="groq", description="NLU backend: claude, groq, or ollama"),
):
    """
    Accepts a WAV audio file upload, transcribes it via Sarvam ASR, then
    extracts structured intent/entities via the NLU layer. Returns the
    parsed NLUResult as JSON - the app displays this for owner review,
    it is NOT saved here.
    """
    suffix = os.path.splitext(file.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    # DEBUG: log the uploaded file size, so we can see in the terminal
    # whether the mobile app is actually sending real audio data or an
    # empty/near-empty file.
    file_size = len(contents)
    print(f"[voice/process-audio] Received file: {file.filename}, size: {file_size} bytes")

    try:
        transcript = transcribe(tmp_path)
        # DEBUG: log the actual transcript text - this tells us definitively
        # whether the mic captured real speech or silence/garbage.
        print(f"[voice/process-audio] ASR transcript: {transcript!r}")

        result = parse_utterance(transcript, backend=backend)
        print(f"[voice/process-audio] Parsed {len(result.transactions)} transaction(s)")
    except Exception as e:
        print(f"[voice/process-audio] ERROR: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        os.unlink(tmp_path)

    return {"status": "success", "result": result.model_dump()}