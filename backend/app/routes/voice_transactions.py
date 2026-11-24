
"""
Voice transaction intake endpoint.

Processes confirmed voice transactions and automatically allocates
customer payments across outstanding bookings using oldest-due-first FIFO.
"""

import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal

sys.path.append(str(Path(__file__).resolve().parents[3]))

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import (
    Booking,
    BookingItem,
    Payment,
    Return,
    UtteranceLog,
)
from app.services.matching import find_or_create_customer, resolve_item_id
from shared.schemas.nlu_schema import NLUResult


router = APIRouter(
    prefix="/voice-transactions",
    tags=["Voice Transactions"],
)


@router.post("/")
def process_voice_transaction(
    nlu_result: NLUResult,
    db: Session = Depends(get_db),
):
    entry_date = datetime.fromisoformat(
        nlu_result.entry_timestamp
    ).date()

    booking_txns = [
        t for t in nlu_result.transactions if t.intent == "BOOKING"
    ]
    payment_txns = [
        t for t in nlu_result.transactions if t.intent == "PAYMENT"
    ]
    return_txns = [
        t for t in nlu_result.transactions if t.intent == "RETURN"
    ]
    query_txns = [
        t for t in nlu_result.transactions if t.intent == "QUERY"
    ]
    complete_txns = [
        t for t in nlu_result.transactions if t.intent == "COMPLETE"
    ]
    cancel_txns = [
        t for t in nlu_result.transactions if t.intent == "CANCEL"
    ]

    results = {
        "bookings": [],
        "payments": [],
        "returns": [],
        "queries": [],
        "completions": [],
        "cancellations": [],
        "errors": [],
    }

    new_booking_ids_by_customer = {}

    try:
        # ---------------- BOOKINGS ----------------

        booking_txns_with_names = [
            t for t in booking_txns if t.customer_name
        ]
        unnamed_booking_txns = [
            t for t in booking_txns if not t.customer_name
        ]

        for txn in unnamed_booking_txns:
            results["errors"].append(
                f"Booking item '{txn.item}' has no customer_name."
            )

        customer_groups = {}

        for txn in booking_txns_with_names:
            customer_groups.setdefault(
                txn.customer_name, []
            ).append(txn)

        for customer_name, group_txns in customer_groups.items():
            customer = find_or_create_customer(db, customer_name)

            event_date_str = group_txns[0].date

            event_date = (
                datetime.strptime(
                    event_date_str, "%Y-%m-%d"
                ).date()
                if event_date_str
                else entry_date
            )

            resolved_items = []

            for txn in group_txns:
                inv, score = resolve_item_id(db, txn.item)

                if inv is None:
                    results["errors"].append(
                        f"Could not match item '{txn.item}' for "
                        f"{customer_name}. Booking NOT created."
                    )
                else:
                    resolved_items.append((txn, inv, score))

            if (
                len(resolved_items) == len(group_txns)
                and resolved_items
            ):
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
                db.flush()

                new_booking_ids_by_customer[
                    customer_name
                ] = booking.booking_id

                for txn, inv, score in resolved_items:
                    item_total = (
                        float(inv.rental_price) * txn.quantity
                    )

                    db.add(
                        BookingItem(
                            booking_id=booking.booking_id,
                            item_id=inv.item_id,
                            quantity=txn.quantity,
                            total_price=item_total,
                        )
                    )

                    if score < 1.0:
                        results["errors"].append(
                            f"NOTE: '{txn.item}' matched "
                            f"'{inv.item_name}' with confidence "
                            f"{score:.2f}. Verify the item."
                        )

                results["bookings"].append({
                    "booking_id": booking.booking_id,
                    "customer": customer.name,
                    "event_date": str(event_date),
                    "total_amount": total_amount,
                    "items": [
                        {
                            "item": inv.item_name,
                            "quantity": txn.quantity,
                        }
                        for txn, inv, _ in resolved_items
                    ],
                })

        # ---------------- PAYMENTS: FIFO ALLOCATION ----------------

        for txn in payment_txns:
            if txn.amount is None:
                results["errors"].append(
                    "Payment transaction has no amount - skipped."
                )
                continue

            if not txn.customer_name:
                results["errors"].append(
                    "Payment has no customer_name - cannot proceed."
                )
                continue

            payment_amount = Decimal(str(txn.amount))

            if payment_amount <= 0:
                results["errors"].append(
                    "Payment amount must be greater than zero."
                )
                continue

            customer = find_or_create_customer(
                db, txn.customer_name
            )

            # Oldest booking first. Cancelled bookings are excluded.
            customer_bookings = (
                db.query(Booking)
                .filter(
                    Booking.customer_id == customer.customer_id,
                    Booking.status != "cancelled",
                )
                .order_by(
                    Booking.booking_date.asc(),
                    Booking.booking_id.asc(),
                )
                .all()
            )

            remaining_payment = payment_amount
            allocated_total = Decimal("0")

            for booking in customer_bookings:
                if remaining_payment <= 0:
                    break

                # Calculate how much this booking has already received.
                existing_payments = (
                    db.query(Payment)
                    .filter(
                        Payment.booking_id == booking.booking_id,
                        Payment.payment_status == "paid",
                    )
                    .all()
                )

                paid_amount = sum(
                    (
                        Decimal(str(p.amount))
                        for p in existing_payments
                        if p.amount is not None
                    ),
                    Decimal("0"),
                )

                booking_total = Decimal(
                    str(booking.total_amount or 0)
                )

                booking_due = max(
                    Decimal("0"),
                    booking_total - paid_amount,
                )

                if booking_due <= 0:
                    continue

                # Allocate only what this booking still owes.
                allocation = min(
                    remaining_payment,
                    booking_due,
                )

                payment = Payment(
                    booking_id=booking.booking_id,
                    amount=allocation,
                    payment_date=entry_date,
                    payment_method="voice",
                    payment_status="paid",
                )

                db.add(payment)
                db.flush()

                remaining_payment -= allocation
                allocated_total += allocation

                results["payments"].append({
                    "booking_id": booking.booking_id,
                    "customer": customer.name,
                    "amount": float(allocation),
                    "remaining_due": float(
                        booking_due - allocation
                    ),
                    "payment_type_from_voice": txn.payment_type,
                })

            if allocated_total == 0:
                results["errors"].append(
                    f"No outstanding balance found for "
                    f"'{txn.customer_name}'. Payment NOT recorded."
                )

            elif remaining_payment > 0:
                results["errors"].append(
                    f"₹{float(allocated_total):.2f} allocated to "
                    f"'{customer.name}'. The remaining "
                    f"₹{float(remaining_payment):.2f} exceeds "
                    f"their outstanding balance and was NOT recorded."
                )

        # ---------------- RETURNS ----------------

        for txn in return_txns:
            if not txn.customer_name:
                results["errors"].append(
                    "Return has no customer_name."
                )
                continue

            customer = find_or_create_customer(
                db, txn.customer_name
            )

            inv, score = resolve_item_id(db, txn.item)

            if inv is None:
                results["errors"].append(
                    f"Could not match returned item '{txn.item}'."
                )
                continue

            matching_booking_item = (
                db.query(BookingItem)
                .join(
                    Booking,
                    Booking.booking_id == BookingItem.booking_id,
                )
                .filter(
                    Booking.customer_id == customer.customer_id,
                    BookingItem.item_id == inv.item_id,
                )
                .order_by(BookingItem.booking_id.desc())
                .first()
            )

            if not matching_booking_item:
                results["errors"].append(
                    f"No matching booking found for "
                    f"'{txn.customer_name}' returning '{txn.item}'."
                )
                continue

            shortfall = (
                matching_booking_item.quantity - txn.quantity
            )

            db.add(
                Return(
                    booking_id=matching_booking_item.booking_id,
                    quantity_returned=txn.quantity,
                    shortfall_flag="YES" if shortfall > 0 else "NO",
                    return_date=entry_date,
                    notes=f"Via voice: {nlu_result.raw_transcript}",
                )
            )

            inv.available_quantity += txn.quantity

            results["returns"].append({
                "booking_id": matching_booking_item.booking_id,
                "item": inv.item_name,
                "quantity_returned": txn.quantity,
                "shortfall": shortfall,
            })

        # ---------------- QUERIES ----------------

        for txn in query_txns:
            results["queries"].append({
                "customer": txn.customer_name,
                "note": (
                    "QUERY intent received but requires "
                    "a separate read-only lookup."
                ),
            })

        # ---------------- COMPLETE / CANCEL ----------------

        def apply_status_change(
            txn,
            new_status,
            results_key,
            verb,
        ):
            if not txn.customer_name:
                results["errors"].append(
                    f"{verb} request has no customer_name."
                )
                return

            customer = find_or_create_customer(
                db, txn.customer_name
            )

            open_bookings = (
                db.query(Booking)
                .filter(
                    Booking.customer_id == customer.customer_id,
                    Booking.status == "confirmed",
                )
                .order_by(Booking.booking_id.desc())
                .all()
            )

            if not open_bookings:
                results["errors"].append(
                    f"No open booking found for "
                    f"'{txn.customer_name}'."
                )
                return

            if len(open_bookings) > 1:
                results["errors"].append(
                    f"'{txn.customer_name}' has "
                    f"{len(open_bookings)} open bookings. "
                    f"Booking IDs: "
                    f"{[b.booking_id for b in open_bookings]}. "
                    f"Nothing changed."
                )
                return

            target_booking = open_bookings[0]
            target_booking.status = new_status

            results[results_key].append({
                "booking_id": target_booking.booking_id,
                "customer": customer.name,
            })

        for txn in complete_txns:
            apply_status_change(
                txn, "completed", "completions", "Complete"
            )

        for txn in cancel_txns:
            apply_status_change(
                txn, "cancelled", "cancellations", "Cancel"
            )

        # ---------------- UTTERANCE LOG ----------------

        any_booking_id = next(
            iter(new_booking_ids_by_customer.values()),
            nlu_result.booking_id,
        )

        db.add(
            UtteranceLog(
                booking_id=any_booking_id,
                raw_text_kn=nlu_result.raw_transcript,
                nlu_json=nlu_result.model_dump_json(),
                confidence=None,
                created_at=entry_date,
            )
        )

        db.commit()

        try:
            from app.services.minio_client import archive_gold

            archive_gold({
                "raw_transcript": nlu_result.raw_transcript,
                "entry_timestamp": nlu_result.entry_timestamp,
                "results": results,
            })

        except Exception as archive_err:
            print(
                "[voice-transactions] MinIO Gold archiving "
                f"failed (non-fatal): {archive_err}"
            )

    except Exception as e:
        db.rollback()

        return {
            "status": "error",
            "message": str(e),
            "partial_results": results,
        }

    return {
        "status": "success",
        "results": results,
    }
