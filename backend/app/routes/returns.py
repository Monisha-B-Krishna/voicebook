from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.database_models import (
    Booking,
    BookingItem,
    Inventory,
    Return
)


router = APIRouter(
    prefix="/returns",
    tags=["Returns"]
)


class ReturnCreate(BaseModel):
    booking_id: int
    item_id: int
    quantity_returned: int
    return_date: date
    notes: str


@router.get("/")
def get_returns(
    db: Session = Depends(get_db)
):

    returns = db.query(Return).all()

    return returns


@router.post("/")
def create_return(
    return_data: ReturnCreate,
    db: Session = Depends(get_db)
):

    # 1. Check whether booking exists
    booking = db.query(Booking).filter(
        Booking.booking_id == return_data.booking_id
    ).first()

    if not booking:
        return {
            "error": "Booking not found"
        }

    # 2. Find the booking item
    booking_item = db.query(BookingItem).filter(
        BookingItem.booking_id == return_data.booking_id,
        BookingItem.item_id == return_data.item_id
    ).first()

    if not booking_item:
        return {
            "error": "Item was not part of this booking"
        }

    # 3. Check returned quantity
    if return_data.quantity_returned > booking_item.quantity:
        return {
            "error": "Returned quantity cannot exceed booked quantity",
            "booked_quantity": booking_item.quantity,
            "requested_return": return_data.quantity_returned
        }

    # 4. Calculate shortfall
    shortfall_quantity = (
        booking_item.quantity - return_data.quantity_returned
    )

    shortfall_flag = (
        "YES" if shortfall_quantity > 0 else "NO"
    )

    # 5. Find inventory item
    inventory_item = db.query(Inventory).filter(
        Inventory.item_id == return_data.item_id
    ).first()

    if not inventory_item:
        return {
            "error": "Inventory item not found"
        }

    # 6. Return the physically returned quantity to inventory
    inventory_item.available_quantity += (
        return_data.quantity_returned
    )

    # 7. Create return record
    return_record = Return(
        booking_id=return_data.booking_id,
        quantity_returned=return_data.quantity_returned,
        shortfall_flag=shortfall_flag,
        return_date=return_data.return_date,
        notes=return_data.notes
    )

    db.add(return_record)
    db.commit()
    db.refresh(return_record)

    return {
        "status": "success",
        "message": "Return processed successfully",
        "booking_id": return_data.booking_id,
        "item_id": return_data.item_id,
        "booked_quantity": booking_item.quantity,
        "quantity_returned": return_data.quantity_returned,
        "shortfall_quantity": shortfall_quantity,
        "shortfall_flag": shortfall_flag,
        "inventory_available": inventory_item.available_quantity,
        "return_id": return_record.return_id
    }