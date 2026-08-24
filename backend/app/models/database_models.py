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
# CUSTOMER ALIASES
# ============================================================
# ADDED FOR DISCUSSION - not yet wired into any endpoint logic.
# Purpose: support "Raju" / "Raju anna" / "Rajashekar" all resolving to
# the same customer, per the project's stated design goal.
#
# OPEN DESIGN QUESTION for the team: how should aliases get added?
#   (a) Automatically, whenever a fuzzy-similar name is spoken again
#       (risk: could silently merge two different real customers)
#   (b) Manually, only when the owner explicitly confirms "yes, same
#       person" (safer, but adds a confirmation step)
# This table is ready either way - the decision affects the service
# logic that writes to it, not the schema itself.

class CustomerAlias(Base):

    __tablename__ = "customer_aliases"

    alias_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    customer_id = Column(
        Integer,
        ForeignKey("customers.customer_id"),
        nullable=False
    )

    alias_name = Column(
        String(100),
        nullable=False
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
