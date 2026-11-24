
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

from fastapi import APIRouter, Depends, HTTPException, Path as ApiPath, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import Customer, CustomerAlias
from app.services.matching import suggest_similar_customers


router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)


# ============================================================
# REQUEST SCHEMAS AND VALIDATION
# ============================================================

class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Customer name cannot be empty")

        return value

    @field_validator("phone", "address")
    @classmethod
    def clean_optional_fields(cls, value):
        if value is not None:
            value = value.strip()
            return value or None

        return value


class AliasCreate(BaseModel):
    alias_name: str = Field(min_length=1, max_length=100)

    @field_validator("alias_name")
    @classmethod
    def validate_alias_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Alias name cannot be empty")

        return value


# ============================================================
# CUSTOMER ENDPOINTS
# ============================================================

@router.get("/")
def get_customers(
    db: Session = Depends(get_db)
):
    return db.query(Customer).all()


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


# ============================================================
# SIMILAR CUSTOMER SEARCH
# ============================================================

@router.get("/similar")
def check_similar_customers(
    name: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db)
):
    """
    Suggests possible existing customer matches.
    Does not automatically merge customers.
    """

    name = name.strip()

    if not name:
        raise HTTPException(
            status_code=422,
            detail="Customer name cannot be empty"
        )

    matches = suggest_similar_customers(db, name)

    return [
        {
            "customer_id": cust.customer_id,
            "name": cust.name,
            "similarity": round(score, 2)
        }
        for cust, score in matches
    ]


# ============================================================
# CUSTOMER ALIASES
# ============================================================

@router.post("/{customer_id}/aliases")
def add_customer_alias(
    customer_id: int = ApiPath(gt=0),
    alias_data: AliasCreate = ...,
    db: Session = Depends(get_db)
):
    """
    Records a confirmed customer alias.
    Duplicate normalized aliases are rejected.
    """

    customer = db.query(Customer).filter(
        Customer.customer_id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    alias = CustomerAlias(
        customer_id=customer_id,
        alias_name=alias_data.alias_name
    )

    db.add(alias)

    try:
        db.commit()
        db.refresh(alias)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="This alias already exists"
        )

    return {
        "status": "success",
        "customer_id": customer_id,
        "alias_name": alias.alias_name
    }


@router.get("/{customer_id}/aliases")
def get_customer_aliases(
    customer_id: int = ApiPath(gt=0),
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.customer_id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    aliases = db.query(CustomerAlias).filter(
        CustomerAlias.customer_id == customer_id
    ).all()

    return [
        {
            "alias_id": alias.alias_id,
            "alias_name": alias.alias_name
        }
        for alias in aliases
    ]


# ============================================================
# CUSTOMER BALANCE
# ============================================================

@router.get("/{customer_id}/balance")
def get_customer_balance(
    customer_id: int = ApiPath(gt=0),
    db: Session = Depends(get_db)
):
    from app.models.database_models import Booking, Payment

    customer = db.query(Customer).filter(
        Customer.customer_id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    bookings = db.query(Booking).filter(
        Booking.customer_id == customer_id,
        Booking.status != "cancelled"
    ).all()

    total_booked = sum(
        float(booking.total_amount)
        for booking in bookings
    )

    booking_ids = [
        booking.booking_id
        for booking in bookings
    ]

    payments = db.query(Payment).filter(
        Payment.booking_id.in_(booking_ids),
        Payment.payment_status == "paid"
    ).all() if booking_ids else []

    total_paid = sum(
        float(payment.amount)
        for payment in payments
    )

    balance = total_booked - total_paid

    import base64 as b64
    from nlp.tts.tts_client import synthesize_audio_bytes

    spoken_text = (
        f"{customer.name} ಗೆ "
        f"{balance:.0f} ರೂಪಾಯಿ ಬಾಕಿ ಇದೆ."
    )

    audio_base64 = None

    try:
        audio_bytes = synthesize_audio_bytes(spoken_text)
        audio_base64 = b64.b64encode(audio_bytes).decode("utf-8")

    except Exception as e:
        print(f"[balance] TTS generation failed: {e}")

    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "total_booked": total_booked,
        "total_paid": total_paid,
        "balance_due": balance,
        "spoken_text": spoken_text,
        "audio_base64": audio_base64
    }


# ============================================================
# CUSTOMER ORDER HISTORY
# ============================================================

@router.get("/{customer_id}/orders")
def get_customer_orders(
    customer_id: int = ApiPath(gt=0),
    db: Session = Depends(get_db)
):
    from app.models.database_models import Booking, BookingItem, Inventory

    customer = db.query(Customer).filter(
        Customer.customer_id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    bookings = db.query(Booking).filter(
        Booking.customer_id == customer_id,
        Booking.status != "cancelled"
    ).order_by(
        Booking.booking_id.desc()
    ).all()

    orders_summary = []
    spoken_parts = []

    for booking in bookings:

        items = (
            db.query(BookingItem, Inventory)
            .join(
                Inventory,
                Inventory.item_id == BookingItem.item_id
            )
            .filter(
                BookingItem.booking_id == booking.booking_id
            )
            .all()
        )

        item_list = [
            {
                "item": inventory.item_name,
                "quantity": booking_item.quantity
            }
            for booking_item, inventory in items
        ]

        orders_summary.append({
            "booking_id": booking.booking_id,
            "event_date": str(booking.event_date),
            "items": item_list
        })

        spoken_parts.extend(item_list)

    if spoken_parts:
        item_totals = {}

        for item in spoken_parts:
            name = item["item"]
            item_totals[name] = item_totals.get(name, 0) + item["quantity"]

        item_phrases = ", ".join(
            f"{quantity} {name}"
            for name, quantity in item_totals.items()
        )

        spoken_text = (
            f"{customer.name} ಗೆ "
            + item_phrases
            + " ಬುಕ್ ಆಗಿದೆ."
        )

    else:
        spoken_text = (
            f"{customer.name} ಗೆ "
            "ಯಾವುದೇ ಬುಕ್ಕಿಂಗ್ ಇಲ್ಲ."
        )

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
        "audio_base64": audio_base64
    }
