"""
Star-schema warehouse tables, per the project proposal: fact_transactions
plus four dimensions (dim_customer, dim_inventory, dim_date, dim_utterance).

These live in the SAME PostgreSQL database as the OLTP tables (a common,
reasonable simplification for a single-pilot-store project - a fully
separate warehouse instance would be overkill here), but as clearly
separate tables, populated only by the Airflow ETL DAG - never written
to directly by the application.

NOTE: dim_customer, dim_date, and fact_booking already existed (built by
Kiruba, in voicebook_etl.py) before this file - fact_booking is a
booking-level summary fact, kept as-is. fact_transactions here is a NEW,
more granular fact table matching the proposal's exact stated design: one
row per individual transaction event (a booked item, a payment, or a
return), each tied to a customer, an inventory item (where applicable), a
date, and the utterance that produced it - giving richer analytical
granularity than fact_booking alone.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Numeric,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import declarative_base

WarehouseBase = declarative_base()


# ============================================================
# DIM_CUSTOMER (already created by Kiruba's ETL DAG logic -
# defined here too so this file can create it if missing)
# ============================================================

class DimCustomer(WarehouseBase):
    __tablename__ = "dim_customer"

    customer_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    address = Column(String(255))


# ============================================================
# DIM_DATE (already created by Kiruba's ETL DAG logic)
# ============================================================

class DimDate(WarehouseBase):
    __tablename__ = "dim_date"

    date_key = Column(Integer, primary_key=True)  # YYYYMMDD
    full_date = Column(Date, nullable=False)
    day = Column(Integer)
    month = Column(Integer)
    month_name = Column(String(20))
    quarter = Column(Integer)
    year = Column(Integer)
    weekday_name = Column(String(20))


# ============================================================
# DIM_INVENTORY (NEW)
# ============================================================

class DimInventory(WarehouseBase):
    __tablename__ = "dim_inventory"

    item_id = Column(Integer, primary_key=True)
    item_name = Column(String(100), nullable=False)
    category = Column(String(100))
    rental_price = Column(Numeric(10, 2))


# ============================================================
# DIM_UTTERANCE (NEW)
# ============================================================
# One row per voice utterance that produced a transaction - lets
# analysts trace "which spoken sentence led to this booking/payment"
# and supports future analysis of ASR/NLU accuracy over time.

class DimUtterance(WarehouseBase):
    __tablename__ = "dim_utterance"

    utterance_id = Column(Integer, primary_key=True)
    raw_text_kn = Column(Text)
    nlu_json = Column(Text)
    confidence = Column(Numeric(5, 4))
    created_at = Column(Date)


# ============================================================
# FACT_BOOKING (already created by Kiruba's ETL DAG logic -
# booking-level summary fact, kept as-is)
# ============================================================

class FactBooking(WarehouseBase):
    __tablename__ = "fact_booking"

    booking_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("dim_customer.customer_id"))
    booking_date = Column(Date)
    event_date = Column(Date)
    total_amount = Column(Numeric(10, 2))
    status = Column(String(50))


# ============================================================
# FACT_TRANSACTIONS (NEW) - the proposal's actual named fact table.
# One row per individual transaction event: a booked item, a payment,
# or a return. transaction_type distinguishes which.
# ============================================================

class FactTransactions(WarehouseBase):
    __tablename__ = "fact_transactions"

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)

    # Distinguishes what kind of event this row represents.
    transaction_type = Column(String(20), nullable=False)  # BOOKING_ITEM / PAYMENT / RETURN

    customer_id = Column(Integer, ForeignKey("dim_customer.customer_id"))
    item_id = Column(Integer, ForeignKey("dim_inventory.item_id"), nullable=True)  # null for PAYMENT rows
    date_key = Column(Integer, ForeignKey("dim_date.date_key"))
    utterance_id = Column(Integer, ForeignKey("dim_utterance.utterance_id"), nullable=True)

    quantity = Column(Integer, nullable=True)   # for BOOKING_ITEM / RETURN
    amount = Column(Numeric(10, 2), nullable=True)  # for PAYMENT, or item_total for BOOKING_ITEM

    # Traceability back to the original OLTP row this was derived from.
    source_table = Column(String(30))   # "booking_items" / "payments" / "returns"
    source_id = Column(Integer)         # booking_item_id / payment_id / return_id
