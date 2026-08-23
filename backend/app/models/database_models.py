from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Numeric,
    ForeignKey,
    Text
)

from sqlalchemy.orm import declarative_base


Base = declarative_base()


# ============================================================
# CUSTOMERS
# ============================================================

class Customer(Base):

    __tablename__ = "customers"

    customer_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    name = Column(
        String(100),
        nullable=False
    )

    phone = Column(
        String(20)
    )

    address = Column(
        String(255)
    )


# ============================================================
# BOOKINGS
# ============================================================

class Booking(Base):

    __tablename__ = "bookings"

    booking_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    customer_id = Column(
        Integer,
        ForeignKey("customers.customer_id"),
        nullable=False
    )

    booking_date = Column(
        Date,
        nullable=False
    )

    event_date = Column(
        Date,
        nullable=False
    )

    total_amount = Column(
        Numeric(10, 2),
        nullable=False
    )

    status = Column(
        String(50),
        nullable=False
    )


# ============================================================
# INVENTORY
# ============================================================

class Inventory(Base):

    __tablename__ = "inventory"

    item_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    item_name = Column(
        String(100),
        nullable=False
    )

    category = Column(
        String(100)
    )

    available_quantity = Column(
        Integer,
        nullable=False
    )

    rental_price = Column(
        Numeric(10, 2),
        nullable=False
    )


# ============================================================
# BOOKING ITEMS
# ============================================================

class BookingItem(Base):

    __tablename__ = "booking_items"

    booking_item_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    booking_id = Column(
        Integer,
        ForeignKey("bookings.booking_id"),
        nullable=False
    )

    item_id = Column(
        Integer,
        ForeignKey("inventory.item_id"),
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False
    )

    total_price = Column(
        Numeric(10, 2),
        nullable=False
    )


# ============================================================
# PAYMENTS
# ============================================================

class Payment(Base):

    __tablename__ = "payments"

    payment_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    booking_id = Column(
        Integer,
        ForeignKey("bookings.booking_id"),
        nullable=False
    )

    amount = Column(
        Numeric(10, 2),
        nullable=False
    )

    payment_date = Column(
        Date,
        nullable=False
    )

    payment_method = Column(
        String(50)
    )

    payment_status = Column(
        String(50),
        nullable=False
    )


# ============================================================
# RETURNS
# ============================================================

class Return(Base):

    __tablename__ = "returns"

    return_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    booking_id = Column(
        Integer,
        ForeignKey("bookings.booking_id"),
        nullable=False
    )

    quantity_returned = Column(
        Integer,
        nullable=False
    )

    shortfall_flag = Column(
        String(10)
    )

    return_date = Column(
        Date,
        nullable=False
    )

    notes = Column(
        String(500)
    )


# ============================================================
# UTTERANCE LOGS
# ============================================================

class UtteranceLog(Base):

    __tablename__ = "utterance_logs"

    utterance_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    booking_id = Column(
        Integer,
        ForeignKey("bookings.booking_id"),
        nullable=True
    )

    raw_text_kn = Column(
        Text
    )

    nlu_json = Column(
        Text
    )

    confidence = Column(
        Numeric(5, 4)
    )

    created_at = Column(
        Date,
        nullable=False
    )