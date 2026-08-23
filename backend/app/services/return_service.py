from datetime import date

from app.data.dummy_data import (
    bookings,
    booking_items,
    returns
)

from app.services.inventory_service import return_inventory


def process_return(data):

    # ========================================================
    # 1. Check booking
    # ========================================================

    booking = None

    for b in bookings:

        if b["booking_id"] == data.booking_id:
            booking = b
            break

    if booking is None:

        return {
            "status": "failed",
            "reason": "Booking not found"
        }


    # ========================================================
    # 2. Find booked item
    # ========================================================

    booked_quantity = None

    for item in booking_items:

        if (
            item["booking_id"] == data.booking_id
            and item["item_id"] == data.item_id
        ):

            booked_quantity = item["quantity"]
            break


    if booked_quantity is None:

        return {
            "status": "failed",
            "reason": "Item was not part of this booking"
        }


    # ========================================================
    # 3. Check returned quantity
    # ========================================================

    if data.quantity_returned > booked_quantity:

        return {

            "status": "failed",

            "reason":
                "Returned quantity cannot exceed booked quantity"
        }


    # ========================================================
    # 4. Determine shortfall
    # ========================================================

    shortfall = (
        data.quantity_returned < booked_quantity
    )


    # ========================================================
    # 5. Return inventory
    # ========================================================

    return_inventory(
        data.item_id,
        data.quantity_returned
    )


    # ========================================================
    # 6. Create return record
    # ========================================================

    return_record = {

        "return_id": len(returns) + 1,

        "booking_id": data.booking_id,

        "quantity_returned":
            data.quantity_returned,

        "shortfall_flag":
            "YES" if shortfall else "NO",

        "return_date":
            date.today(),

        "notes":
            data.notes
    }


    returns.append(return_record)


    return {

        "status": "success",

        "message": "Return processed successfully",

        "return": return_record
    }