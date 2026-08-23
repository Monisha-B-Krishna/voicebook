from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import BookingItem, Inventory, Booking
from pydantic import BaseModel


router = APIRouter(
    prefix="/booking-items",
    tags=["Booking Items"]
)

class BookingItemCreate(BaseModel):
    booking_id: int
    item_id: int
    quantity: int
    total_price: float

@router.get("/")
def get_booking_items(
    db: Session = Depends(get_db)
):

    booking_items = db.query(BookingItem).all()

    return booking_items

@router.post("/")
def create_booking_item(
    item_data: BookingItemCreate,
    db: Session = Depends(get_db)
):

    # 1. Find the booking
    booking = db.query(Booking).filter(
        Booking.booking_id == item_data.booking_id
    ).first()

    if not booking:
        return {
            "error": "Booking not found"
        }

    # 2. Find the inventory item
    inventory_item = db.query(Inventory).filter(
        Inventory.item_id == item_data.item_id
    ).first()

    if not inventory_item:
        return {
            "error": "Inventory item not found"
        }

    # 3. Find existing bookings for the same
    #    inventory item on the same event date
    existing_booking_items = (
        db.query(BookingItem)
        .join(
            Booking,
            Booking.booking_id == BookingItem.booking_id
        )
        .filter(
            BookingItem.item_id == item_data.item_id,
            Booking.event_date == booking.event_date,
            Booking.status != "cancelled"
        )
        .all()
    )

    # 4. Calculate already booked quantity
    booked_quantity = sum(
        item.quantity
        for item in existing_booking_items
    )

    # 5. Calculate remaining inventory
    available_for_date = (
        inventory_item.available_quantity - booked_quantity
    )

    # 6. Check availability
    if item_data.quantity > available_for_date:
        return {
            "error": "Insufficient inventory for this event date",
            "total_inventory": inventory_item.available_quantity,
            "already_booked": booked_quantity,
            "available": available_for_date,
            "requested": item_data.quantity,
            "event_date": booking.event_date
        }

    # 7. Create booking item
    booking_item = BookingItem(
        booking_id=item_data.booking_id,
        item_id=item_data.item_id,
        quantity=item_data.quantity,
        total_price=item_data.total_price
    )

    # 8. Save to PostgreSQL
    db.add(booking_item)
    db.commit()
    db.refresh(booking_item)

    return booking_item