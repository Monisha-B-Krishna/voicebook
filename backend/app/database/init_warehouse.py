"""
Creates the star-schema warehouse tables (dim_customer, dim_date,
dim_inventory, dim_utterance, fact_booking, fact_transactions) in the
same PostgreSQL database as the OLTP tables.

Run this ONCE before running the voicebook_etl Airflow DAG - the DAG
inserts INTO these tables, it doesn't create them.

Usage: python -m app.database.init_warehouse
"""

from app.database.connection import engine
from app.models.warehouse_models import WarehouseBase


def init_warehouse():
    WarehouseBase.metadata.create_all(bind=engine)
    print("VoiceBook warehouse tables created successfully.")


if __name__ == "__main__":
    init_warehouse()
