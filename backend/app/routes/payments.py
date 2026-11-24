
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import Booking, Payment


router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


class PaymentCreate(BaseModel):
    booking_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    payment_date: date
    payment_method: Optional[str] = Field(
        default=None,
        max_length=50
    )
    payment_status: str = Field(
        min_length=1,
        max_length=50
    )

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Payment method cannot be empty")
        return value

    @field_validator("payment_status")
    @classmethod
    def validate_payment_status(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Payment status cannot be empty")
        return value


@router.get("/")
def get_payments(
    db: Session = Depends(get_db)
):
    return db.query(Payment).all()


@router.post("/")
def create_payment(
    payment_data: PaymentCreate,
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(
        Booking.booking_id == payment_data.booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    existing_payments = db.query(Payment).filter(
        Payment.booking_id == payment_data.booking_id,
        Payment.payment_status == "paid"
    ).all()

    paid_amount = sum(
        (Decimal(str(payment.amount)) for payment in existing_payments),
        Decimal("0.00")
    )

    booking_total = Decimal(str(booking.total_amount))
    remaining_amount = booking_total - paid_amount

    if payment_data.amount > remaining_amount:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Payment exceeds remaining booking amount",
                "booking_total": str(booking_total),
                "already_paid": str(paid_amount),
                "remaining": str(remaining_amount),
                "requested": str(payment_data.amount)
            }
        )

    payment = Payment(
        booking_id=payment_data.booking_id,
        amount=payment_data.amount,
        payment_date=payment_data.payment_date,
        payment_method=payment_data.payment_method,
        payment_status=payment_data.payment_status
    )

    try:
        db.add(payment)
        db.commit()
        db.refresh(payment)
    except Exception:
        db.rollback()
        raise

    return payment
