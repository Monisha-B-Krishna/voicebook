"""
Lightweight transcribe-only endpoint: for short replies (yes/no
confirmations) where running the FULL NLU pipeline would be wasteful -
we just need the words, not structured intent extraction.
"""

import sys
import tempfile
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))  # project root

from fastapi import APIRouter, UploadFile, File

from nlp.asr.asr_client import transcribe


router = APIRouter(
    prefix="/voice",
    tags=["Voice Audio Intake"]
)


@router.post("/transcribe-only")
async def transcribe_only(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        transcript = transcribe(tmp_path)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        os.unlink(tmp_path)

    return {"status": "success", "transcript": transcript}
