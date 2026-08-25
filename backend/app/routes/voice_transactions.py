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
    new_booking_ids_by_customer = {}  # customer_name -> booking_id, for same-utterance payment attachment

    try:
        # ---------------- BOOKING(S) ----------------
        # Booking transactions are grouped BY their own customer_name, not
        # assumed to all belong to one customer - a single utterance CAN
        # contain bookings for two different people (e.g. "Raju ge 50
        # chair, Raju anna ge 10 plates"), so each distinct customer named
        # gets their own Booking row.
        booking_txns_with_names = [t for t in booking_txns if t.customer_name]
        unnamed_booking_txns = [t for t in booking_txns if not t.customer_name]

        for txn in unnamed_booking_txns:
            results["errors"].append(
                f"Booking item '{txn.item}' has no customer_name - cannot proceed with this item."
            )

        customer_groups = {}
        for txn in booking_txns_with_names:
            customer_groups.setdefault(txn.customer_name, []).append(txn)

        for customer_name, group_txns in customer_groups.items():
            customer = find_or_create_customer(db, customer_name)

            # event_date: use this group's first explicit date if present,
            # otherwise default to entry_date (today).
            event_date_str = group_txns[0].date
            event_date = (
                datetime.strptime(event_date_str, "%Y-%m-%d").date()
                if event_date_str else entry_date
            )

            # Resolve every item in THIS customer's group first - if any
            # item can't be matched, reject only this customer's booking,
            # not the whole request.
            resolved_items = []
            for txn in group_txns:
                inv, score = resolve_item_id(db, txn.item)
                if inv is None:
                    results["errors"].append(
                        f"Could not match item '{txn.item}' (for {customer_name}) to any "
                        f"inventory item. This booking NOT created - please add this item "
                        f"to inventory or correct the item name."
                    )
                else:
                    resolved_items.append((txn, inv, score))

            if len(resolved_items) == len(group_txns) and resolved_items:
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
                new_booking_ids_by_customer[customer_name] = booking.booking_id

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
            target_booking_id = new_booking_ids_by_customer.get(txn.customer_name)  # payment in same utterance as a booking, for THIS customer

            if target_booking_id is None:
                # No booking created in THIS request - find the customer's
                # bookings to attach payment to.
                if not txn.customer_name:
                    results["errors"].append("Payment has no customer_name - cannot proceed.")
                    continue

                customer = find_or_create_customer(db, txn.customer_name)
                open_bookings = (
                    db.query(Booking)
                    .filter(Booking.customer_id == customer.customer_id, Booking.status != "cancelled")
                    .order_by(Booking.booking_id.desc())
                    .all()
                )

                if not open_bookings:
                    results["errors"].append(
                        f"No existing booking found for '{txn.customer_name}' to attach this payment to."
                    )
                    continue

                if len(open_bookings) > 1:
                    # SAFETY FIX: don't silently guess which booking this
                    # payment belongs to - that risk was flagged as a real
                    # gap. Instead, fail clearly and list the options so a
                    # human (or a future disambiguation voice prompt) can
                    # resolve it correctly.
                    results["errors"].append(
                        f"'{txn.customer_name}' has {len(open_bookings)} open bookings - "
                        f"cannot determine which one this payment is for. "
                        f"Booking IDs: {[b.booking_id for b in open_bookings]}. "
                        f"Payment NOT recorded - please specify which booking."
                    )
                    continue

                target_booking_id = open_bookings[0].booking_id

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
        # If multiple bookings were created (multiple customers in one
        # utterance), just log against the first one - this log is a
        # convenience reference, not the source of truth (nlu_json below
        # has the complete picture regardless).
        any_booking_id = next(iter(new_booking_ids_by_customer.values()), None)
        log_entry = UtteranceLog(
            booking_id=any_booking_id,
            raw_text_kn=nlu_result.raw_transcript,
            nlu_json=nlu_result.model_dump_json(),
            confidence=None,  # no confidence score currently produced by the NLU layer
            created_at=entry_date,
        )
        db.add(log_entry)

        db.commit()

        # Gold: the final, validated, curated result - AFTER the database
        # write succeeded. Non-fatal if MinIO archiving fails - the actual
        # transaction is already safely committed regardless.
        try:
            from app.services.minio_client import archive_gold
            archive_gold({
                "raw_transcript": nlu_result.raw_transcript,
                "entry_timestamp": nlu_result.entry_timestamp,
                "results": results,
            })
        except Exception as archive_err:
            print(f"[voice-transactions] MinIO Gold archiving failed (non-fatal): {archive_err}")

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e), "partial_results": results}

    return {"status": "success", "results": results}

