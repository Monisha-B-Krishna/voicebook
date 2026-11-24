
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
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
    booking_id: int = Field(gt=0)
    item_id: int = Field(gt=0)
    quantity_returned: int = Field(gt=0)
    return_date: date
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                return None
        return value


@router.get("/")
def get_returns(
    db: Session = Depends(get_db)
):
    return db.query(Return).all()


@router.post("/")
def create_return(
    return_data: ReturnCreate,
    db: Session = Depends(get_db)
):
    try:
        booking = db.query(Booking).filter(
            Booking.booking_id == return_data.booking_id
        ).with_for_update().first()

        if not booking:
            raise HTTPException(
                status_code=404,
                detail="Booking not found"
            )

        booked_quantity = db.query(
            func.coalesce(func.sum(BookingItem.quantity), 0)
        ).filter(
            BookingItem.booking_id == return_data.booking_id,
            BookingItem.item_id == return_data.item_id
        ).scalar()

        booked_quantity = int(booked_quantity or 0)

        if booked_quantity <= 0:
            raise HTTPException(
                status_code=404,
                detail="Item was not part of this booking"
            )

        previous_returns = db.query(
            func.coalesce(func.sum(Return.quantity_returned), 0)
        ).filter(
            Return.booking_id == return_data.booking_id,
            Return.item_id == return_data.item_id
        ).scalar()

        already_returned = int(previous_returns or 0)

        remaining_quantity = (
            booked_quantity - already_returned
        )

        if return_data.quantity_returned > remaining_quantity:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Returned quantity exceeds the remaining booked quantity",
                    "booked_quantity": booked_quantity,
                    "already_returned": already_returned,
                    "remaining_quantity": remaining_quantity,
                    "requested_return": return_data.quantity_returned
                }
            )

        inventory_item = db.query(Inventory).filter(
            Inventory.item_id == return_data.item_id
        ).with_for_update().first()

        if not inventory_item:
            raise HTTPException(
                status_code=404,
                detail="Inventory item not found"
            )

        shortfall_quantity = (
            remaining_quantity - return_data.quantity_returned
        )

        shortfall_flag = (
            "YES" if shortfall_quantity > 0 else "NO"
        )

        inventory_item.available_quantity += (
            return_data.quantity_returned
        )

        return_record = Return(
            booking_id=return_data.booking_id,
            item_id=return_data.item_id,
            quantity_returned=return_data.quantity_returned,
            shortfall_flag=shortfall_flag,
            return_date=return_data.return_date,
            notes=return_data.notes
        )

        db.add(return_record)
        db.commit()

        db.refresh(return_record)
        db.refresh(inventory_item)

        return {
            "status": "success",
            "message": "Return processed successfully",
            "booking_id": return_data.booking_id,
            "item_id": return_data.item_id,
            "booked_quantity": booked_quantity,
            "previously_returned": already_returned,
            "quantity_returned": return_data.quantity_returned,
            "remaining_shortfall": shortfall_quantity,
            "shortfall_flag": shortfall_flag,
            "inventory_available": inventory_item.available_quantity,
            "return_id": return_record.return_id
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise
