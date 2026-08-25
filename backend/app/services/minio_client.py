"""
MinIO client wrapper implementing the proposal's Bronze/Silver/Gold
medallion architecture:
  - Bronze: raw audio files + raw ASR transcript output
  - Silver: NLU-structured JSON (extracted intents/entities)
  - Gold: validated, curated JSON after successful database write

Buckets are created automatically on first use if they don't exist.
Connects to the MinIO instance already running via docker-compose
(localhost:9000, since the backend runs on the host machine, not inside
the docker network - same reasoning as connection.py's use of
"localhost" instead of "postgres" for the database).
"""

import os
import json
from datetime import datetime
from minio import Minio
from minio.error import S3Error
import io

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")

BRONZE_BUCKET = "voicebook-bronze"
SILVER_BUCKET = "voicebook-silver"
GOLD_BUCKET = "voicebook-gold"

_client = None


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,  # local docker instance, no TLS
        )
        _ensure_buckets_exist(_client)
    return _client


def _ensure_buckets_exist(client: Minio):
    for bucket in (BRONZE_BUCKET, SILVER_BUCKET, GOLD_BUCKET):
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)


def _timestamped_key(prefix: str, extension: str) -> str:
    timestamp = datetime.now().strftime("%Y/%m/%d/%H%M%S_%f")
    return f"{prefix}/{timestamp}.{extension}"


def archive_bronze(audio_bytes: bytes, asr_transcript: str) -> dict:
    """
    Archives the raw audio file and raw ASR output. Returns the object
    keys used, for reference/logging.
    """
    client = get_client()

    audio_key = _timestamped_key("audio", "wav")
    client.put_object(
        BRONZE_BUCKET, audio_key,
        io.BytesIO(audio_bytes), length=len(audio_bytes),
        content_type="audio/wav",
    )

    transcript_key = _timestamped_key("asr_transcript", "json")
    transcript_payload = json.dumps({"transcript": asr_transcript}, ensure_ascii=False).encode("utf-8")
    client.put_object(
        BRONZE_BUCKET, transcript_key,
        io.BytesIO(transcript_payload), length=len(transcript_payload),
        content_type="application/json",
    )

    return {"audio_key": audio_key, "transcript_key": transcript_key}


def archive_silver(nlu_result_dict: dict) -> str:
    """
    Archives the NLU-structured JSON (extracted intents/entities) -
    the output of the NLU layer, before database resolution.
    """
    client = get_client()

    key = _timestamped_key("nlu_result", "json")
    payload = json.dumps(nlu_result_dict, ensure_ascii=False, default=str).encode("utf-8")
    client.put_object(
        SILVER_BUCKET, key,
        io.BytesIO(payload), length=len(payload),
        content_type="application/json",
    )
    return key


def archive_gold(validated_result_dict: dict) -> str:
    """
    Archives the final, validated, curated result - AFTER the database
    write succeeded. This is what actually got committed (resolved
    customer/item IDs, computed totals, any errors), ready for the
    warehouse ETL to eventually pick up.
    """
    client = get_client()

    key = _timestamped_key("confirmed_transaction", "json")
    payload = json.dumps(validated_result_dict, ensure_ascii=False, default=str).encode("utf-8")
    client.put_object(
        GOLD_BUCKET, key,
        io.BytesIO(payload), length=len(payload),
        content_type="application/json",
    )
    return key
