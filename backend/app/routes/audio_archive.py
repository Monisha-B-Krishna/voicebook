
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.minio_client import (
    archive_uploaded_audio,
    list_uploaded_audio,
    delete_uploaded_audio,
)

router = APIRouter(
    prefix="/audio-archive",
    tags=["Audio Archive"],
)

MAX_FILE_SIZE = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".flac",
    ".webm",
}

ALLOWED_CONTENT_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/aac",
    "audio/ogg",
    "audio/flac",
    "audio/webm",
    "application/octet-stream",
}


@router.post("/")
async def upload_audio(
    file: UploadFile = File(...),
    transcript: str = Form(default=None),
    language: str = Form(default=None),
):
    filename = file.filename or "audio"
    extension = filename.lower().rsplit(".", 1)

    if len(extension) < 2:
        raise HTTPException(
            status_code=400,
            detail="Audio file must have a valid extension.",
        )

    suffix = "." + extension[-1]

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported audio format.",
        )

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported audio content type.",
        )

    contents = await file.read(MAX_FILE_SIZE + 1)

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Uploaded audio file is empty.",
        )

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Audio file exceeds the 50 MB limit.",
        )

    try:
        metadata = archive_uploaded_audio(
            audio_bytes=contents,
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
            transcript=transcript,
            language=language,
        )

        return {
            "status": "success",
            "message": "Audio archived successfully.",
            "audio": metadata,
        }

    except Exception as exc:
        print(f"[audio-archive] Upload failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not archive audio.",
        )

    finally:
        await file.close()


@router.get("/")
def get_audio_archive():
    try:
        recordings = list_uploaded_audio()

        return {
            "status": "success",
            "count": len(recordings),
            "items": recordings,
        }

    except Exception as exc:
        print(f"[audio-archive] Listing failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve audio archive.",
        )


@router.delete("/{audio_id}")
def remove_audio_archive(audio_id: int):
    deleted = delete_uploaded_audio(audio_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Audio recording not found or could not be deleted.",
        )

    return {
        "status": "success",
        "message": "Audio recording deleted successfully.",
    }
