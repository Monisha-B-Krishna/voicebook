"""
Aggregate/cross-customer analytics endpoints - answers questions that
span MULTIPLE customers or items, as opposed to the per-customer
questions in customers.py (balance, orders for one named customer).

These back voice queries like:
  - "which customers have a balance?" / "who owes more than 5000?"
  - "how many people have booked chairs?" / "how many chairs are left?"
"""

import sys
import base64 as b64
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))  # project root

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import Customer, Booking, Payment, Inventory, BookingItem
from app.services.matching import resolve_item_id
from nlp.tts.tts_client import synthesize_audio_bytes


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


@router.get("/customers-with-balance")
def customers_with_balance(
    min_amount: float = Query(default=0.0, description="Only include customers owing more than this amount"),
    db: Session = Depends(get_db)
):
    """
    Lists customers whose outstanding balance exceeds min_amount.
    min_amount=0 (the default) answers "which customers have a balance
    at all?" - a specific threshold answers "who owes more than X?".
    """
    customers = db.query(Customer).all()
    results = []

    for cust in customers:
        bookings = db.query(Booking).filter(
            Booking.customer_id == cust.customer_id,
            Booking.status != "cancelled"
        ).all()
        if not bookings:
            continue

        total_booked = sum(float(b.total_amount) for b in bookings)
        booking_ids = [b.booking_id for b in bookings]
        payments = db.query(Payment).filter(
            Payment.booking_id.in_(booking_ids),
            Payment.payment_status == "paid"
        ).all()
        total_paid = sum(float(p.amount) for p in payments)
        balance = total_booked - total_paid

        if balance > min_amount:
            results.append({"customer_id": cust.customer_id, "name": cust.name, "balance_due": balance})

    results.sort(key=lambda r: r["balance_due"], reverse=True)

    if results:
        names_phrase = ", ".join(f"{r['name']} ({r['balance_due']:.0f})" for r in results[:5])
        more_note = f" ಮತ್ತು ಇನ್ನೂ {len(results) - 5}" if len(results) > 5 else ""
        if min_amount > 0:
            spoken_text = f"{len(results)} customers ge {min_amount:.0f} rupees ಗಿಂತ ಜಾಸ್ತಿ ಬಾಕಿ ಇದೆ: {names_phrase}{more_note}."
        else:
            spoken_text = f"{len(results)} customers ge ಬಾಕಿ ಇದೆ: {names_phrase}{more_note}."
    else:
        spoken_text = "ಯಾವ customer ಗೂ ಬಾಕಿ ಇಲ್ಲ." if min_amount == 0 else \
            f"ಯಾವ customer ಗೂ {min_amount:.0f} rupees ಗಿಂತ ಜಾಸ್ತಿ ಬಾಕಿ ಇಲ್ಲ."

    audio_base64 = None
    try:
        audio_bytes = synthesize_audio_bytes(spoken_text)
        audio_base64 = b64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"[analytics] TTS generation failed: {e}")

    return {
        "count": len(results),
        "customers": results,
        "spoken_text": spoken_text,
        "audio_base64": audio_base64,
    }


@router.get("/item-status")
def item_status(
    item_name: str = Query(..., description="Spoken item name, e.g. 'chair'"),
    db: Session = Depends(get_db)
):
    """
    Answers both "how many customers have booked <item>?" and "how much
    <item> is remaining?" in one call, since both questions are about the
    same item and naturally asked together.
    """
    inv, score = resolve_item_id(db, item_name)
    if inv is None:
        return {"error": f"Could not match '{item_name}' to any inventory item."}

    booked_count = (
        db.query(BookingItem)
        .join(Booking, Booking.booking_id == BookingItem.booking_id)
        .filter(BookingItem.item_id == inv.item_id, Booking.status != "cancelled")
        .count()
    )

    spoken_text = (
        f"{inv.item_name} ge ಇಲ್ಲಿಯವರೆಗೆ {booked_count} bookings ಆಗಿದೆ, "
        f"{inv.available_quantity} stock ನಲ್ಲಿ ಇದೆ."
    )

    audio_base64 = None
    try:
        audio_bytes = synthesize_audio_bytes(spoken_text)
        audio_base64 = b64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"[analytics] TTS generation failed: {e}")

    return {
        "item_name": inv.item_name,
        "booked_count": booked_count,
        "available_quantity": inv.available_quantity,
        "match_confidence": score,
        "spoken_text": spoken_text,
        "audio_base64": audio_base64,
    }
