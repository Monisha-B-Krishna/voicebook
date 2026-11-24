
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Numeric,
    ForeignKey,
    Text,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


# ============================================================
# CUSTOMERS
# ============================================================

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    address = Column(String(255))

    bookings = relationship("Booking", back_populates="customer")
    aliases = relationship("CustomerAlias", back_populates="customer")


# ============================================================
# BOOKINGS
# ============================================================

class Booking(Base):
    __tablename__ = "bookings"

    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0",
            name="chk_booking_total_nonnegative"
        ),
    )

    booking_id = Column(Integer, primary_key=True, autoincrement=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.customer_id"),
        nullable=False
    )

    booking_date = Column(Date, nullable=False)
    event_date = Column(Date, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), nullable=False)

    customer = relationship("Customer", back_populates="bookings")
    booking_items = relationship("BookingItem", back_populates="booking")
    payments = relationship("Payment", back_populates="booking")
    returns = relationship("Return", back_populates="booking")
    utterance_logs = relationship("UtteranceLog", back_populates="booking")


# ============================================================
# INVENTORY
# ============================================================

class Inventory(Base):
    __tablename__ = "inventory"

    __table_args__ = (
        CheckConstraint(
            "available_quantity >= 0",
            name="chk_inventory_quantity_nonnegative"
        ),
        CheckConstraint(
            "rental_price >= 0",
            name="chk_inventory_price_nonnegative"
        ),
    )

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    item_name = Column(String(100), nullable=False)
    category = Column(String(100))
    available_quantity = Column(Integer, nullable=False)
    rental_price = Column(Numeric(10, 2), nullable=False)

    booking_items = relationship(
        "BookingItem",
        back_populates="inventory_item"
    )

    returns = relationship(
        "Return",
        back_populates="inventory_item"
    )


# ============================================================
# BOOKING ITEMS
# ============================================================

class BookingItem(Base):
    __tablename__ = "booking_items"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="chk_booking_item_quantity_positive"
        ),
        CheckConstraint(
            "total_price >= 0",
            name="chk_booking_item_price_nonnegative"
        ),
    )

    booking_item_id = Column(Integer, primary_key=True, autoincrement=True)

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

    quantity = Column(Integer, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    booking = relationship("Booking", back_populates="booking_items")

    inventory_item = relationship(
        "Inventory",
        back_populates="booking_items"
    )


# ============================================================
# PAYMENTS
# ============================================================

class Payment(Base):
    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint(
            "amount >= 0",
            name="chk_payment_amount_nonnegative"
        ),
    )

    payment_id = Column(Integer, primary_key=True, autoincrement=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.booking_id"),
        nullable=False
    )

    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    payment_method = Column(String(50))
    payment_status = Column(String(50), nullable=False)

    booking = relationship("Booking", back_populates="payments")


# ============================================================
# RETURNS
# ============================================================

class Return(Base):
    __tablename__ = "returns"

    __table_args__ = (
        CheckConstraint(
            "quantity_returned >= 0",
            name="chk_return_quantity_nonnegative"
        ),
    )

    return_id = Column(Integer, primary_key=True, autoincrement=True)

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

    quantity_returned = Column(Integer, nullable=False)
    shortfall_flag = Column(String(10))
    return_date = Column(Date, nullable=False)
    notes = Column(String(500))

    booking = relationship("Booking", back_populates="returns")

    inventory_item = relationship(
        "Inventory",
        back_populates="returns"
    )


# ============================================================
# CUSTOMER ALIASES
# ============================================================

class CustomerAlias(Base):
    __tablename__ = "customer_aliases"

    alias_id = Column(Integer, primary_key=True, autoincrement=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.customer_id"),
        nullable=False
    )

    alias_name = Column(String(100), nullable=False)

    customer = relationship("Customer", back_populates="aliases")


Index(
    "uq_customer_alias_normalized",
    func.lower(func.trim(CustomerAlias.alias_name)),
    unique=True
)


# ============================================================
# UTTERANCE LOGS
# ============================================================

class UtteranceLog(Base):
    __tablename__ = "utterance_logs"

    __table_args__ = (
        CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="chk_utterance_confidence_range"
        ),
    )

    utterance_id = Column(Integer, primary_key=True, autoincrement=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.booking_id"),
        nullable=True
    )

    raw_text_kn = Column(Text)
    nlu_json = Column(Text)
    confidence = Column(Numeric(5, 4))
    created_at = Column(Date, nullable=False)

    booking = relationship("Booking", back_populates="utterance_logs")
