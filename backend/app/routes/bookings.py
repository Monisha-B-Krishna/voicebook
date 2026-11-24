
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import Booking


router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"]
)


class BookingCreate(BaseModel):
    customer_id: int = Field(gt=0)
    booking_date: date
    event_date: date
    total_amount: float = Field(ge=0, allow_inf_nan=False)
    status: str = Field(min_length=1, max_length=50)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Booking status cannot be empty")

        return value

    @model_validator(mode="after")
    def validate_event_date(self):
        if self.event_date < self.booking_date:
            raise ValueError("Event date cannot be before booking date")

        return self


@router.get("/")
def get_bookings(
    db: Session = Depends(get_db)
):
    bookings = db.query(Booking).all()
    return bookings


@router.post("/")
def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db)
):
    booking = Booking(
        customer_id=booking_data.customer_id,
        booking_date=booking_data.booking_date,
        event_date=booking_data.event_date,
        total_amount=booking_data.total_amount,
        status=booking_data.status
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return booking
