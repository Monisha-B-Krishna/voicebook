from datetime import date

from app.data.dummy_data import payments, bookings


def get_booking(booking_id):

    for booking in bookings:

        if booking["booking_id"] == booking_id:
            return booking

    return None


def create_payment(data):

    booking = get_booking(data.booking_id)

    if booking is None:

        return {
            "status": "failed",
            "reason": "Booking not found"
        }


    # --------------------------------------------------------
    # Calculate already paid amount
    # --------------------------------------------------------

    already_paid = 0

    for payment in payments:

        if payment["booking_id"] == data.booking_id:

            if payment["payment_status"] == "successful":

                already_paid += payment["amount"]


    # --------------------------------------------------------
    # Prevent overpayment
    # --------------------------------------------------------

    remaining = (
        booking["total_amount"]
        - already_paid
    )

    if data.amount > remaining:

        return {
            "status": "failed",
            "reason": "Payment exceeds remaining balance",
            "remaining_amount": remaining
        }


    # --------------------------------------------------------
    # Create payment
    # --------------------------------------------------------

    payment = {

        "payment_id": len(payments) + 1,

        "booking_id": data.booking_id,

        "amount": data.amount,

        "payment_date": date.today(),

        "payment_method": data.payment_method,

        "payment_status": "successful"
    }


    payments.append(payment)


    return {

        "status": "success",

        "message": "Payment recorded successfully",

        "payment": payment,

        "remaining_balance":
            remaining - data.amount
    }