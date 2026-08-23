from datetime import date

from app.data.dummy_data import bookings, booking_items

from app.services.customer_service import get_customer

from app.services.inventory_service import (
    get_inventory_item,
    check_availability,
    reserve_inventory
)


def create_booking(data):

    # ========================================================
    # 1. Check customer
    # ========================================================

    customer = get_customer(data.customer_id)

    if customer is None:

        return {
            "status": "failed",
            "reason": "Customer not found"
        }


    # ========================================================
    # 2. Check every requested inventory item
    #    BEFORE changing inventory
    # ========================================================

    for requested_item in data.items:

        availability = check_availability(
            requested_item.item_id,
            requested_item.quantity
        )

        if not availability["available"]:

            return {
                "status": "failed",
                "reason": availability["reason"],
                "item_id": requested_item.item_id
            }


    # ========================================================
    # 3. Calculate total amount
    # ========================================================

    total_amount = 0

    calculated_items = []

    for requested_item in data.items:

        item = get_inventory_item(
            requested_item.item_id
        )

        item_total = (
            item["rental_price"]
            * requested_item.quantity
        )

        total_amount += item_total

        calculated_items.append({
            "item_id": item["item_id"],
            "quantity": requested_item.quantity,
            "total_price": item_total
        })


    # ========================================================
    # 4. Generate booking ID
    # ========================================================

    booking_id = len(bookings) + 1


    # ========================================================
    # 5. Create booking
    # ========================================================

    booking = {

        "booking_id": booking_id,

        "customer_id": customer["customer_id"],

        "booking_date": date.today(),

        "event_date": data.event_date,

        "total_amount": total_amount,

        "status": "confirmed"
    }


    bookings.append(booking)


    # ========================================================
    # 6. Create booking items
    # ========================================================

    for calculated_item in calculated_items:

        booking_item = {

            "booking_item_id": len(booking_items) + 1,

            "booking_id": booking_id,

            "item_id": calculated_item["item_id"],

            "quantity": calculated_item["quantity"],

            "total_price": calculated_item["total_price"]
        }

        booking_items.append(booking_item)


    # ========================================================
    # 7. Reserve inventory
    # ========================================================

    for calculated_item in calculated_items:

        reserve_inventory(
            calculated_item["item_id"],
            calculated_item["quantity"]
        )


    # ========================================================
    # 8. Return confirmation
    # ========================================================

    return {

        "status": "success",

        "message": "Booking created successfully",

        "booking": booking,

        "booking_items": calculated_items
    }