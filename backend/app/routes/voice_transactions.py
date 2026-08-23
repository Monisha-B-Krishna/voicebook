"""
Voice transaction intake endpoint - THE integration point between the NLP
layer (Monisha) and the business logic layer (Kiruba).

Accepts an NLUResult (the exact same Pydantic contract used in
shared/schemas/nlu_schema.py) and orchestrates the full write: resolving
customer/item names to database IDs, creating booking + items + payment/
return records, and logging the raw utterance - all in ONE database
transaction, so a failure partway through rolls back cleanly instead of
leaving a half-created booking in the database.

This endpoint should only be called AFTER the owner has confirmed the
transaction via voice (the NLP layer's confirmation gate) - it assumes
what it receives has already been approved.
"""

import sys
import json
from pathlib import Path
from datetime import date, datetime

sys.path.append(str(Path(__file__).resolve().parents[3]))  # project root

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import Booking, BookingItem, Payment, Return, UtteranceLog
from app.services.matching import find_or_create_customer, resolve_item_id
from shared.schemas.nlu_schema import NLUResult


router = APIRouter(
    prefix="/voice-transactions",
    tags=["Voice Transactions"]
)


@router.post("/")
def process_voice_transaction(
    nlu_result: NLUResult,
    db: Session = Depends(get_db)
):
    """
    Processes one confirmed NLUResult (which may contain multiple
    transactions from a single utterance - e.g. a multi-item booking, or
    a booking + payment together).
    """
    entry_date = datetime.fromisoformat(nlu_result.entry_timestamp).date()

    # Group BOOKING transactions together - a multi-item booking from one
    # utterance ("30 chairs, 20 pathre") produces multiple Transaction
    # objects that should become ONE Booking row + multiple BookingItem
    # rows, not multiple separate bookings.
    booking_txns = [t for t in nlu_result.transactions if t.intent == "BOOKING"]
    payment_txns = [t for t in nlu_result.transactions if t.intent == "PAYMENT"]
    return_txns = [t for t in nlu_result.transactions if t.intent == "RETURN"]
    query_txns = [t for t in nlu_result.transactions if t.intent == "QUERY"]

    results = {"bookings": [], "payments": [], "returns": [], "queries": [], "errors": []}
    new_booking_id = None  # if this request creates a booking, payments in
                             # the SAME request attach to it automatically

    try:
        # ---------------- BOOKING(S) ----------------
        if booking_txns:
            # All booking transactions in one utterance share the same
            # customer - use the first one's customer_name for the group.
            customer_name = booking_txns[0].customer_name
            if not customer_name:
                results["errors"].append("Booking has no customer_name - cannot proceed.")
            else:
                customer = find_or_create_customer(db, customer_name)

                # event_date: use the explicit date if the NLU resolved one,
                # otherwise default to entry_date (today) - matches the
                # documented design: "owner speaking today with no date
                # mentioned means today, unless corrected."
                event_date_str = booking_txns[0].date
                event_date = (
                    datetime.strptime(event_date_str, "%Y-%m-%d").date()
                    if event_date_str else entry_date
                )

                # Resolve every item first, before creating anything - if
                # ANY item can't be matched to inventory, reject the whole
                # booking rather than silently creating a partial/wrong one.
                resolved_items = []
                for txn in booking_txns:
                    inv, score = resolve_item_id(db, txn.item)
                    if inv is None:
                        results["errors"].append(
                            f"Could not match item '{txn.item}' to any inventory item. "
                            f"Booking NOT created - please add this item to inventory "
                            f"or correct the item name."
                        )
                    else:
                        resolved_items.append((txn, inv, score))

                if len(resolved_items) == len(booking_txns) and resolved_items:
                    total_amount = sum(
                        float(inv.rental_price) * txn.quantity
                        for txn, inv, _ in resolved_items
                    )

                    booking = Booking(
                        customer_id=customer.customer_id,
                        booking_date=entry_date,
                        event_date=event_date,
                        total_amount=total_amount,
                        status="confirmed",
                    )
                    db.add(booking)
                    db.flush()  # get booking_id without committing yet
                    new_booking_id = booking.booking_id

                    for txn, inv, score in resolved_items:
                        item_total = float(inv.rental_price) * txn.quantity
                        booking_item = BookingItem(
                            booking_id=booking.booking_id,
                            item_id=inv.item_id,
                            quantity=txn.quantity,
                            total_price=item_total,
                        )
                        db.add(booking_item)
                        if score < 1.0:
                            results["errors"].append(
                                f"NOTE: item '{txn.item}' fuzzy-matched to "
                                f"'{inv.item_name}' (confidence {score:.2f}) - verify this is correct."
                            )

                    results["bookings"].append({
                        "booking_id": booking.booking_id,
                        "customer": customer.name,
                        "event_date": str(event_date),
                        "total_amount": total_amount,
                        "items": [
                            {"item": inv.item_name, "quantity": txn.quantity}
                            for txn, inv, _ in resolved_items
                        ],
                    })

        # ---------------- PAYMENT(S) ----------------
        for txn in payment_txns:
            target_booking_id = new_booking_id  # payment in same utterance as a booking

            if target_booking_id is None:
                # No booking created in THIS request - find the customer's
                # most recent non-cancelled booking to attach payment to.
                # LIMITATION: this is a best-effort guess when the owner
                # says something like "Suresh paid 2000" with no booking
                # context in the same utterance. If a customer has multiple
                # open bookings, this could attach to the wrong one - a
                # real system might ask the owner to disambiguate by voice
                # ("which booking - the June 15 one or the July 3 one?").
                # Flagging this as a design gap, not fixing here.
                if not txn.customer_name:
                    results["errors"].append("Payment has no customer_name - cannot proceed.")
                    continue

                customer = find_or_create_customer(db, txn.customer_name)
                latest_booking = (
                    db.query(Booking)
                    .filter(Booking.customer_id == customer.customer_id, Booking.status != "cancelled")
                    .order_by(Booking.booking_id.desc())
                    .first()
                )
                if not latest_booking:
                    results["errors"].append(
                        f"No existing booking found for '{txn.customer_name}' to attach this payment to."
                    )
                    continue
                target_booking_id = latest_booking.booking_id

            if txn.amount is None:
                results["errors"].append("Payment transaction has no amount - skipped.")
                continue

            payment = Payment(
                booking_id=target_booking_id,
                amount=txn.amount,
                payment_date=entry_date,
                payment_method="voice",  # NLU's payment_type (advance/balance) isn't
                                          # currently a DB field - logged in notes instead
                payment_status="paid",
            )
            db.add(payment)
            results["payments"].append({
                "booking_id": target_booking_id,
                "amount": txn.amount,
                "payment_type_from_voice": txn.payment_type,
            })

        # ---------------- RETURN(S) ----------------
        for txn in return_txns:
            if not txn.customer_name:
                results["errors"].append("Return has no customer_name - cannot proceed.")
                continue

            customer = find_or_create_customer(db, txn.customer_name)
            inv, score = resolve_item_id(db, txn.item)
            if inv is None:
                results["errors"].append(f"Could not match returned item '{txn.item}' to inventory.")
                continue

            # Find the most recent booking_item for this customer + item
            matching_booking_item = (
                db.query(BookingItem)
                .join(Booking, Booking.booking_id == BookingItem.booking_id)
                .filter(Booking.customer_id == customer.customer_id, BookingItem.item_id == inv.item_id)
                .order_by(BookingItem.booking_id.desc())
                .first()
            )
            if not matching_booking_item:
                results["errors"].append(
                    f"No matching booking found for '{txn.customer_name}' returning '{txn.item}'."
                )
                continue

            shortfall = matching_booking_item.quantity - txn.quantity
            return_record = Return(
                booking_id=matching_booking_item.booking_id,
                quantity_returned=txn.quantity,
                shortfall_flag="YES" if shortfall > 0 else "NO",
                return_date=entry_date,
                notes=f"Via voice: {nlu_result.raw_transcript}",
            )
            db.add(return_record)

            # give back the returned quantity to inventory
            inv.available_quantity += txn.quantity

            results["returns"].append({
                "booking_id": matching_booking_item.booking_id,
                "item": inv.item_name,
                "quantity_returned": txn.quantity,
                "shortfall": shortfall,
            })

        # ---------------- QUERY(IES) ----------------
        # QUERY intent is read-only (e.g. "what does Suresh owe?") - not
        # implemented in this WRITE endpoint. A real system would route
        # these to a separate read-only lookup, not this transaction path.
        for txn in query_txns:
            results["queries"].append({
                "customer": txn.customer_name,
                "note": "QUERY intent received but not processed here - "
                        "needs a separate read-only balance-lookup endpoint.",
            })

        # ---------------- LOG THE RAW UTTERANCE ----------------
        log_entry = UtteranceLog(
            booking_id=new_booking_id,
            raw_text_kn=nlu_result.raw_transcript,
            nlu_json=nlu_result.model_dump_json(),
            confidence=None,  # no confidence score currently produced by the NLU layer
            created_at=entry_date,
        )
        db.add(log_entry)

        db.commit()

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e), "partial_results": results}

    return {"status": "success", "results": results}
