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

This is the same principle as the local nlp/demo/full_demo_pipeline.py
scaffold (parse first, confirm, then save) - just reachable over HTTP
instead of running as a local script, since a phone can't run Python
scripts directly.
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
    # Save the uploaded audio to a temp file, since asr_client.transcribe()
    # expects a file path (matching how it's used in the local pipeline).
    suffix = os.path.splitext(file.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        transcript = transcribe(tmp_path)
        result = parse_utterance(transcript, backend=backend)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        os.unlink(tmp_path)  # clean up the temp file regardless of success/failure

    return {"status": "success", "result": result.model_dump()}
