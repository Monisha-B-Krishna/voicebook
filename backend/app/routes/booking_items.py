
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import BookingItem, Inventory, Booking


router = APIRouter(
    prefix="/booking-items",
    tags=["Booking Items"]
)


class BookingItemCreate(BaseModel):
    booking_id: int = Field(gt=0)
    item_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    total_price: float = Field(ge=0)


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
    # 1. Find the booking
    booking = (
        db.query(Booking)
        .filter(Booking.booking_id == item_data.booking_id)
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    # 2. Find the inventory item
    inventory_item = (
        db.query(Inventory)
        .filter(Inventory.item_id == item_data.item_id)
        .first()
    )

    if not inventory_item:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found"
        )

    # 3. Prevent adding items to cancelled bookings
    if (booking.status or "").strip().lower() in {
        "cancelled", "canceled"
    }:
        raise HTTPException(
            status_code=400,
            detail="Cannot add items to a cancelled booking"
        )

    # 4. Find quantities booked for the same item and event date
    existing_booking_items = (
        db.query(BookingItem)
        .join(
            Booking,
            Booking.booking_id == BookingItem.booking_id
        )
        .filter(
            BookingItem.item_id == item_data.item_id,
            Booking.event_date == booking.event_date
        )
        .all()
    )

    # 5. Count only items belonging to active bookings
    booked_quantity = sum(
        item.quantity
        for item in existing_booking_items
        if (
            db.query(Booking.status)
            .filter(Booking.booking_id == item.booking_id)
            .scalar() or ""
        ).strip().lower() not in {"cancelled", "canceled"}
    )

    # 6. Calculate remaining stock
    available_for_date = max(
        0,
        inventory_item.available_quantity - booked_quantity
    )

    # 7. Reject requests exceeding available stock
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

    # 8. Create the booking item
    booking_item = BookingItem(
        booking_id=item_data.booking_id,
        item_id=item_data.item_id,
        quantity=item_data.quantity,
        total_price=item_data.total_price
    )

    # 9. Save to PostgreSQL
    db.add(booking_item)
    db.commit()
    db.refresh(booking_item)

    return booking_item
