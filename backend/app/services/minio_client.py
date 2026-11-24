
import os
import json
import io
import time
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

from minio import Minio

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")

PLAYBACK_MINIO_ENDPOINT = os.getenv(
    "PLAYBACK_MINIO_ENDPOINT",
    "10.159.185.7:9000",
)

BRONZE_BUCKET = "voicebook-bronze"
SILVER_BUCKET = "voicebook-silver"
GOLD_BUCKET = "voicebook-gold"

AUDIO_RETENTION_DAYS = 20

_client = None
_playback_client = None


def get_client() -> Minio:
    global _client

    if _client is None:
        _client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )
        _ensure_buckets_exist(_client)

    return _client


def get_playback_client() -> Minio:
    global _playback_client

    if _playback_client is None:
        _playback_client = Minio(
            PLAYBACK_MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )

    return _playback_client


def _ensure_buckets_exist(client):
    for bucket in (BRONZE_BUCKET, SILVER_BUCKET, GOLD_BUCKET):
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)


def _timestamped_key(prefix: str, extension: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d/%H%M%S_%f")
    return f"{prefix}/{timestamp}.{extension}"


def _put_json(bucket: str, key: str, payload: dict):
    client = get_client()
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    client.put_object(
        bucket,
        key,
        io.BytesIO(encoded),
        length=len(encoded),
        content_type="application/json",
    )


def _read_json(bucket: str, key: str) -> dict:
    client = get_client()
    response = client.get_object(bucket, key)

    try:
        return json.loads(response.read().decode("utf-8"))
    finally:
        response.close()
        response.release_conn()


# EXISTING BRONZE ARCHIVING

def archive_bronze(audio_bytes: bytes, asr_transcript: str) -> dict:
    client = get_client()

    audio_key = _timestamped_key("audio", "wav")

    client.put_object(
        BRONZE_BUCKET,
        audio_key,
        io.BytesIO(audio_bytes),
        length=len(audio_bytes),
        content_type="audio/wav",
    )

    transcript_key = _timestamped_key("asr_transcript", "json")

    _put_json(
        BRONZE_BUCKET,
        transcript_key,
        {
            "transcript": asr_transcript,
            "audio_key": audio_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "audio_key": audio_key,
        "transcript_key": transcript_key,
    }


# MANUAL AUDIO UPLOAD ARCHIVE

def archive_uploaded_audio(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    transcript: str = None,
    language: str = None,
) -> dict:
    client = get_client()

    archive_id = int(time.time() * 1_000_000)
    safe_filename = Path(filename).name or "audio"
    extension = Path(safe_filename).suffix.lower() or ".audio"

    audio_key = (
        f"uploaded_audio/{archive_id}_{uuid.uuid4().hex}{extension}"
    )

    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(days=AUDIO_RETENTION_DAYS)

    client.put_object(
        BRONZE_BUCKET,
        audio_key,
        io.BytesIO(audio_bytes),
        length=len(audio_bytes),
        content_type=content_type or "application/octet-stream",
    )

    metadata = {
        "id": archive_id,
        "filename": safe_filename,
        "audio_key": audio_key,
        "content_type": content_type,
        "size": len(audio_bytes),
        "transcript": transcript,
        "language": language,
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat(),
    }

    metadata_key = f"uploaded_metadata/{archive_id}.json"
    _put_json(BRONZE_BUCKET, metadata_key, metadata)

    return metadata


def list_uploaded_audio() -> list:
    client = get_client()
    playback_client = get_playback_client()
    results = []

    objects = client.list_objects(
        BRONZE_BUCKET,
        prefix="uploaded_metadata/",
        recursive=True,
    )

    for obj in objects:
        if not obj.object_name.endswith(".json"):
            continue

        try:
            metadata = _read_json(BRONZE_BUCKET, obj.object_name)

            metadata["playback_url"] = playback_client.presigned_get_object(
                BRONZE_BUCKET,
                metadata["audio_key"],
                expires=timedelta(hours=1),
            )

            results.append(metadata)

        except Exception as exc:
            print(
                f"[MinIO] Could not read archive "
                f"{obj.object_name}: {exc}"
            )

    results.sort(
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )

    return results


def delete_uploaded_audio(archive_id: int) -> bool:
    client = get_client()

    metadata_key = f"uploaded_metadata/{archive_id}.json"

    try:
        metadata = _read_json(BRONZE_BUCKET, metadata_key)

        client.remove_object(
            BRONZE_BUCKET,
            metadata["audio_key"],
        )

        client.remove_object(
            BRONZE_BUCKET,
            metadata_key,
        )

        return True

    except Exception as exc:
        print(f"[MinIO] Archive deletion failed: {exc}")
        return False


# AUTOMATIC 20-DAY RETENTION CLEANUP

def cleanup_expired_audio() -> int:
    client = get_client()

    cutoff = datetime.now(timezone.utc) - timedelta(
        days=AUDIO_RETENTION_DAYS
    )

    deleted_count = 0

    prefixes = (
        "audio/",
        "asr_transcript/",
        "uploaded_audio/",
        "uploaded_metadata/",
    )

    for prefix in prefixes:
        objects = client.list_objects(
            BRONZE_BUCKET,
            prefix=prefix,
            recursive=True,
        )

        for obj in objects:
            if obj.last_modified and obj.last_modified < cutoff:
                try:
                    client.remove_object(
                        BRONZE_BUCKET,
                        obj.object_name,
                    )
                    deleted_count += 1

                    print(
                        f"[MinIO] Expired audio archive deleted: "
                        f"{obj.object_name}"
                    )

                except Exception as exc:
                    print(
                        f"[MinIO] Cleanup failed for "
                        f"{obj.object_name}: {exc}"
                    )

    print(
        f"[MinIO] Retention cleanup completed. "
        f"Deleted {deleted_count} expired objects."
    )

    return deleted_count


# EXISTING SILVER ARCHIVING

def archive_silver(nlu_result_dict: dict) -> str:
    key = _timestamped_key("nlu_result", "json")
    _put_json(SILVER_BUCKET, key, nlu_result_dict)
    return key


# EXISTING GOLD ARCHIVING

def archive_gold(validated_result_dict: dict) -> str:
    key = _timestamped_key("confirmed_transaction", "json")
    _put_json(GOLD_BUCKET, key, validated_result_dict)
    return key
