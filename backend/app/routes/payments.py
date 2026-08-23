from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import Booking, Payment


router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


class PaymentCreate(BaseModel):
    booking_id: int
    amount: float
    payment_date: date
    payment_method: str
    payment_status: str


@router.get("/")
def get_payments(
    db: Session = Depends(get_db)
):
    payments = db.query(Payment).all()
    return payments


@router.post("/")
def create_payment(
    payment_data: PaymentCreate,
    db: Session = Depends(get_db)
):

    # 1. Check whether booking exists
    booking = db.query(Booking).filter(
        Booking.booking_id == payment_data.booking_id
    ).first()

    if not booking:
        return {
            "error": "Booking not found"
        }

    # 2. Find all successful payments for this booking
    existing_payments = db.query(Payment).filter(
        Payment.booking_id == payment_data.booking_id,
        Payment.payment_status == "paid"
    ).all()

    # 3. Calculate already paid amount
    paid_amount = sum(
        payment.amount
        for payment in existing_payments
    )

    # 4. Calculate remaining booking amount
    remaining_amount = booking.total_amount - paid_amount

    # 5. Prevent overpayment
    if payment_data.amount > remaining_amount:
        return {
            "error": "Payment exceeds remaining booking amount",
            "booking_total": booking.total_amount,
            "already_paid": paid_amount,
            "remaining": remaining_amount,
            "requested": payment_data.amount
        }

    # 6. Create payment
    payment = Payment(
        booking_id=payment_data.booking_id,
        amount=payment_data.amount,
        payment_date=payment_data.payment_date,
        payment_method=payment_data.payment_method,
        payment_status=payment_data.payment_status
    )

    # 7. Save payment
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment