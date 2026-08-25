import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[3]))  # project root

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import Customer, CustomerAlias
from app.services.matching import suggest_similar_customers


router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)


class CustomerCreate(BaseModel):
    name: str
    phone: str = None
    address: str = None


class AliasCreate(BaseModel):
    alias_name: str


@router.get("/")
def get_customers(
    db: Session = Depends(get_db)
):

    customers = db.query(Customer).all()

    return customers


@router.post("/")
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db)
):

    customer = Customer(
        name=customer_data.name,
        phone=customer_data.phone,
        address=customer_data.address
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


@router.get("/similar")
def check_similar_customers(
    name: str,
    db: Session = Depends(get_db)
):
    """
    Called by the NLP client BEFORE finalizing a transaction, to check if
    a spoken customer name might be an existing customer under a slightly
    different name/nickname. Per team decision: this only SUGGESTS matches
    - it never auto-merges. The owner must be asked and confirm via voice;
    if confirmed, the client calls POST /customers/{id}/aliases to record it.
    """
    matches = suggest_similar_customers(db, name)
    return [
        {"customer_id": cust.customer_id, "name": cust.name, "similarity": round(score, 2)}
        for cust, score in matches
    ]


@router.post("/{customer_id}/aliases")
def add_customer_alias(
    customer_id: int,
    alias_data: AliasCreate,
    db: Session = Depends(get_db)
):
    """
    Records a confirmed alias - only called AFTER the owner has verbally
    confirmed "yes, same person" for a suggested match from /similar.
    """
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        return {"error": "Customer not found"}

    alias = CustomerAlias(customer_id=customer_id, alias_name=alias_data.alias_name.strip())
    db.add(alias)
    db.commit()
    db.refresh(alias)

    return {"status": "success", "customer_id": customer_id, "alias_name": alias.alias_name}


@router.get("/{customer_id}/aliases")
def get_customer_aliases(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Lists confirmed aliases for a customer - needed by the mobile app's
    customer search (which searches name + aliases, per Customer.matches
    in the Flutter model)."""
    aliases = db.query(CustomerAlias).filter(CustomerAlias.customer_id == customer_id).all()
    return [{"alias_id": a.alias_id, "alias_name": a.alias_name} for a in aliases]


@router.get("/{customer_id}/balance")
def get_customer_balance(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """
    Computes a customer's total outstanding balance: sum of total_amount
    across their non-cancelled bookings, minus sum of their paid payments.
    This is what answers a QUERY intent like "Suresh estu baaki
    haakidaane?" (how much does Suresh owe?).
    """
    from app.models.database_models import Booking, Payment

    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        return {"error": "Customer not found"}

    bookings = db.query(Booking).filter(
        Booking.customer_id == customer_id,
        Booking.status != "cancelled"
    ).all()

    total_booked = sum(float(b.total_amount) for b in bookings)

    booking_ids = [b.booking_id for b in bookings]
    payments = db.query(Payment).filter(
        Payment.booking_id.in_(booking_ids),
        Payment.payment_status == "paid"
    ).all() if booking_ids else []

    total_paid = sum(float(p.amount) for p in payments)

    balance = total_booked - total_paid

    # Generate a spoken Kannada-English answer, base64-encoded, for the
    # mobile app to play directly - reuses the same Sarvam TTS client the
    # desktop demo pipeline uses, just without local playback.
    import base64 as b64
    from nlp.tts.tts_client import synthesize_audio_bytes

    spoken_text = f"{customer.name} ge {balance:.0f} rupees baaki ide."
    audio_base64 = None
    try:
        audio_bytes = synthesize_audio_bytes(spoken_text)
        audio_base64 = b64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        # If TTS fails (e.g. Sarvam credits exhausted), still return the
        # numeric answer - the app can fall back to showing text only.
        print(f"[balance] TTS generation failed: {e}")

    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "total_booked": total_booked,
        "total_paid": total_paid,
        "balance_due": balance,
        "spoken_text": spoken_text,
        "audio_base64": audio_base64,
    }


@router.get("/{customer_id}/orders")
def get_customer_orders(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """
    Answers "what did this customer order?" type questions - lists their
    bookings with items, as opposed to /balance which answers "how much
    do they owe?". These are genuinely different questions and need
    different answers, not the same balance lookup reused for both.
    """
    from app.models.database_models import Booking, BookingItem, Inventory

    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        return {"error": "Customer not found"}

    bookings = db.query(Booking).filter(
        Booking.customer_id == customer_id,
        Booking.status != "cancelled"
    ).order_by(Booking.booking_id.desc()).all()

    orders_summary = []
    spoken_parts = []

    for booking in bookings:
        items = (
            db.query(BookingItem, Inventory)
            .join(Inventory, Inventory.item_id == BookingItem.item_id)
            .filter(BookingItem.booking_id == booking.booking_id)
            .all()
        )
        item_list = [{"item": inv.item_name, "quantity": bi.quantity} for bi, inv in items]
        orders_summary.append({
            "booking_id": booking.booking_id,
            "event_date": str(booking.event_date),
            "items": item_list,
        })

        item_phrases = ", ".join(f"{i['quantity']} {i['item']}" for i in item_list)
        if item_phrases:
            spoken_parts.append(item_phrases)

    if spoken_parts:
        spoken_text = f"{customer.name} ge " + "; ".join(spoken_parts) + " book agide."
    else:
        spoken_text = f"{customer.name} ge yaava booking illa."

    import base64 as b64
    from nlp.tts.tts_client import synthesize_audio_bytes

    audio_base64 = None
    try:
        audio_bytes = synthesize_audio_bytes(spoken_text)
        audio_base64 = b64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"[orders] TTS generation failed: {e}")

    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "orders": orders_summary,
        "spoken_text": spoken_text,
        "audio_base64": audio_base64,
    }
