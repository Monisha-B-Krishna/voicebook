
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import (
    BookingItem,
    Inventory,
    Booking
)


router = APIRouter(
    prefix="/booking-items",
    tags=["Booking Items"]
)


class BookingItemCreate(BaseModel):
    booking_id: int = Field(gt=0)
    item_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    total_price: Decimal = Field(
        ge=0,
        max_digits=10,
        decimal_places=2
    )


@router.get("/")
def get_booking_items(
    db: Session = Depends(get_db)
):
    return db.query(BookingItem).all()


@router.post("/")
def create_booking_item(
    item_data: BookingItemCreate,
    db: Session = Depends(get_db)
):
    try:
        booking = db.query(Booking).filter(
            Booking.booking_id == item_data.booking_id
        ).first()

        if not booking:
            raise HTTPException(
                status_code=404,
                detail="Booking not found"
            )

        inventory_item = db.query(Inventory).filter(
            Inventory.item_id == item_data.item_id
        ).first()

        if not inventory_item:
            raise HTTPException(
                status_code=404,
                detail="Inventory item not found"
            )

        if (booking.status or "").strip().lower() in {
            "cancelled", "canceled"
        }:
            raise HTTPException(
                status_code=400,
                detail="Cannot add items to a cancelled booking"
            )

        existing_booking_items = (
            db.query(BookingItem)
            .join(
                Booking,
                Booking.booking_id == BookingItem.booking_id
            )
            .filter(
                BookingItem.item_id == item_data.item_id,
                Booking.event_date == booking.event_date,
                Booking.status.notin_(["cancelled", "canceled"])
            )
            .all()
        )

        booked_quantity = sum(
            item.quantity for item in existing_booking_items
        )

        available_for_date = max(
            0,
            inventory_item.available_quantity - booked_quantity
        )

        if item_data.quantity > available_for_date:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Insufficient inventory for this event date",
                    "total_inventory": inventory_item.available_quantity,
                    "already_booked": booked_quantity,
                    "available": available_for_date,
                    "requested": item_data.quantity,
                    "event_date": booking.event_date.isoformat()
                }
            )

        booking_item = BookingItem(
            booking_id=item_data.booking_id,
            item_id=item_data.item_id,
            quantity=item_data.quantity,
            total_price=item_data.total_price
        )

        db.add(booking_item)
        db.commit()
        db.refresh(booking_item)

        return booking_item

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise
