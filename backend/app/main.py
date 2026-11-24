
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.customers import router as customers_router
from app.routes.inventory import router as inventory_router
from app.routes.bookings import router as bookings_router
from app.routes.booking_items import router as booking_items_router
from app.routes.payments import router as payments_router
from app.routes.returns import router as returns_router
from app.routes.voice_transactions import router as voice_transactions_router
from app.routes.voice_audio import router as voice_audio_router
from app.routes.voice_transcribe import router as voice_transcribe_router
from app.routes.tts import router as tts_router
from app.routes.analytics import router as analytics_router
from app.routes.audio_archive import router as audio_archive_router

from app.services.minio_client import cleanup_expired_audio


async def audio_cleanup_scheduler():
    while True:
        try:
            deleted = await asyncio.to_thread(cleanup_expired_audio)
            print(
                f"[Audio Retention] Cleanup completed. "
                f"Deleted {deleted} expired objects."
            )
        except Exception as exc:
            print(f"[Audio Retention] Cleanup failed: {exc}")

        await asyncio.sleep(24 * 60 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(audio_cleanup_scheduler())

    yield

    cleanup_task.cancel()

    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="VoiceBook Backend",
    description="Business Logic API for VoiceBook",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customers_router)
app.include_router(inventory_router)
app.include_router(bookings_router)
app.include_router(booking_items_router)
app.include_router(payments_router)
app.include_router(returns_router)
app.include_router(voice_transactions_router)
app.include_router(voice_audio_router)
app.include_router(voice_transcribe_router)
app.include_router(tts_router)
app.include_router(analytics_router)
app.include_router(audio_archive_router)


@app.get("/")
def home():
    return {
        "message": "VoiceBook Backend is running"
    }
