
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import Inventory, BookingItem, Booking


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)


@router.get("/")
def get_inventory(
    db: Session = Depends(get_db)
):
    return db.query(Inventory).all()


@router.get("/availability")
def check_inventory_availability(
    event_date: date = Query(
        ...,
        description="Event date in YYYY-MM-DD format"
    ),
    item_id: int = Query(
        ...,
        gt=0,
        description="Inventory item ID"
    ),
    quantity: int = Query(
        ...,
        gt=0,
        description="Quantity requested"
    ),
    db: Session = Depends(get_db)
):
    # 1. Find the inventory item
    inventory_item = (
        db.query(Inventory)
        .filter(Inventory.item_id == item_id)
        .first()
    )

    if not inventory_item:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found"
        )

    # 2. Find quantities already booked for this date
    existing_items = (
        db.query(BookingItem)
        .join(
            Booking,
            Booking.booking_id == BookingItem.booking_id
        )
        .filter(
            BookingItem.item_id == item_id,
            Booking.event_date == event_date,
            Booking.status.notin_(["cancelled", "canceled"])
        )
        .all()
    )

    # 3. Calculate remaining stock
    booked_quantity = sum(
        item.quantity for item in existing_items
    )

    available_quantity = max(
        0,
        inventory_item.available_quantity - booked_quantity
    )

    # 4. Return the availability result without changing data
    return {
        "item_id": inventory_item.item_id,
        "item_name": inventory_item.item_name,
        "event_date": event_date.isoformat(),
        "total_inventory": inventory_item.available_quantity,
        "already_booked": booked_quantity,
        "available_quantity": available_quantity,
        "requested_quantity": quantity,
        "is_available": quantity <= available_quantity
    }
