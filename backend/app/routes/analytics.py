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
    min_amount: float = Query(0.0, ge=0),
    db: Session = Depends(get_db)
):
    from decimal import Decimal

    threshold = Decimal(str(min_amount))
    customer_balances = []

    customers = db.query(Customer).all()

    for customer in customers:
        outstanding = Decimal("0.00")

        for booking in customer.bookings:
            if booking.status.lower() == "cancelled":
                continue

            paid_amount = sum(
                (
                    Decimal(str(payment.amount))
                    for payment in booking.payments
                    if payment.payment_status.lower() == "paid"
                ),
                Decimal("0.00")
            )

            booking_total = Decimal(str(booking.total_amount))
            remaining = max(
                Decimal("0.00"),
                booking_total - paid_amount
            )

            outstanding += remaining

        if outstanding > threshold:
            customer_balances.append({
                "customer_id": customer.customer_id,
                "customer_name": customer.name,
                "outstanding_balance": float(outstanding)
            })

    customer_balances.sort(
        key=lambda x: x["outstanding_balance"],
        reverse=True
    )

    total_outstanding = sum(
        (
            Decimal(str(c["outstanding_balance"]))
            for c in customer_balances
        ),
        Decimal("0.00")
    )

    if customer_balances:
        details = "; ".join(
            f'{c["customer_name"]} owes '
            f'{c["outstanding_balance"]:.2f}'
            for c in customer_balances
        )

        spoken_text = (
            f"Customers with outstanding balances: {details}. "
            f"Total outstanding amount: {total_outstanding:.2f}."
        )
    else:
        spoken_text = (
            f"No customers have an outstanding balance "
            f"above {float(threshold):.2f}."
        )

    audio_base64 = None

    try:
        audio_bytes = synthesize_audio_bytes(spoken_text)
        audio_base64 = b64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"[analytics] TTS generation failed: {e}")

    return {
        "customers": customer_balances,
        "customer_count": len(customer_balances),
        "total_outstanding": float(total_outstanding),
        "min_amount": float(threshold),
        "spoken_text": spoken_text,
        "audio_base64": audio_base64
    }


@router.get("/item-status")
def item_status(
    item_name: str = Query(..., description="Spoken item name, e.g. 'chair'"),
    db: Session = Depends(get_db)
):
    """
    Returns total inventory, total booked quantity,
    remaining quantity and number of bookings.
    """
    inv, score = resolve_item_id(db, item_name)

    if inv is None:
        return {
            "error": f"Could not match '{item_name}' to any inventory item."
        }

    booking_rows = (
        db.query(BookingItem)
        .join(
            Booking,
            Booking.booking_id == BookingItem.booking_id
        )
        .filter(
            BookingItem.item_id == inv.item_id,
            Booking.status != "cancelled"
        )
        .all()
    )

    booked_quantity = sum(
        item.quantity for item in booking_rows
    )

    booking_count = len(booking_rows)

    remaining_quantity = max(
        0,
        inv.available_quantity - booked_quantity
    )

    spoken_text = (
        f"{inv.item_name}: Total stock {inv.available_quantity}, "
        f"{booked_quantity} booked, "
        f"{remaining_quantity} remaining."
    )

    audio_base64 = None

    try:
        audio_bytes = synthesize_audio_bytes(spoken_text)
        audio_base64 = b64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"[analytics] TTS generation failed: {e}")

    return {
        "item_name": inv.item_name,
        "total_inventory": inv.available_quantity,
        "booked_quantity": booked_quantity,
        "remaining_quantity": remaining_quantity,
        "booking_count": booking_count,
        "match_confidence": score,
        "spoken_text": spoken_text,
        "audio_base64": audio_base64,
    }
