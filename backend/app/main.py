from fastapi import FastAPI


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

app = FastAPI(
    title="VoiceBook Backend",
    description="Business Logic API for VoiceBook",
    version="1.0.0"
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


@app.get("/")
def home():
    return {
        "message": "VoiceBook Backend is running"
    }
