from datetime import datetime

import psycopg2

from airflow import DAG
from airflow.operators.python import PythonOperator


DB_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "database": "voicebook",
    "user": "voicebook",
    "password": "voicebook_password"
}


# ============================================================
# LOAD CUSTOMER DIMENSION
# ============================================================

def load_dim_customer():

    connection = psycopg2.connect(**DB_CONFIG)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO dim_customer (
            customer_id,
            name,
            phone,
            address
        )

        SELECT
            customer_id,
            name,
            phone,
            address

        FROM customers

        ON CONFLICT (customer_id)
        DO UPDATE SET
            name = EXCLUDED.name,
            phone = EXCLUDED.phone,
            address = EXCLUDED.address;
    """)

    connection.commit()

    cursor.execute("""
        SELECT COUNT(*)
        FROM dim_customer;
    """)

    count = cursor.fetchone()[0]

    print(f"dim_customer contains {count} records")

    cursor.close()
    connection.close()


# ============================================================
# LOAD INVENTORY DIMENSION (NEW)
# ============================================================

def load_dim_inventory():

    connection = psycopg2.connect(**DB_CONFIG)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO dim_inventory (
            item_id,
            item_name,
            category,
            rental_price
        )

        SELECT
            item_id,
            item_name,
            category,
            rental_price

        FROM inventory

        ON CONFLICT (item_id)
        DO UPDATE SET
            item_name = EXCLUDED.item_name,
            category = EXCLUDED.category,
            rental_price = EXCLUDED.rental_price;
    """)

    connection.commit()

    cursor.execute("SELECT COUNT(*) FROM dim_inventory;")
    count = cursor.fetchone()[0]
    print(f"dim_inventory contains {count} records")

    cursor.close()
    connection.close()


# ============================================================
# LOAD UTTERANCE DIMENSION (NEW)
# ============================================================

def load_dim_utterance():

    connection = psycopg2.connect(**DB_CONFIG)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO dim_utterance (
            utterance_id,
            raw_text_kn,
            nlu_json,
            confidence,
            created_at
        )

        SELECT
            utterance_id,
            raw_text_kn,
            nlu_json,
            confidence,
            created_at

        FROM utterance_logs

        ON CONFLICT (utterance_id)
        DO UPDATE SET
            raw_text_kn = EXCLUDED.raw_text_kn,
            nlu_json = EXCLUDED.nlu_json,
            confidence = EXCLUDED.confidence,
            created_at = EXCLUDED.created_at;
    """)

    connection.commit()

    cursor.execute("SELECT COUNT(*) FROM dim_utterance;")
    count = cursor.fetchone()[0]
    print(f"dim_utterance contains {count} records")

    cursor.close()
    connection.close()


# ============================================================
# LOAD BOOKING FACT
# ============================================================

def load_fact_booking():

    connection = psycopg2.connect(**DB_CONFIG)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO fact_booking (
            booking_id,
            customer_id,
            booking_date,
            event_date,
            total_amount,
            status
        )

        SELECT
            booking_id,
            customer_id,
            booking_date,
            event_date,
            total_amount,
            status

        FROM bookings

        ON CONFLICT (booking_id)
        DO UPDATE SET
            customer_id = EXCLUDED.customer_id,
            booking_date = EXCLUDED.booking_date,
            event_date = EXCLUDED.event_date,
            total_amount = EXCLUDED.total_amount,
            status = EXCLUDED.status;
    """)

    connection.commit()

    cursor.execute("""
        SELECT COUNT(*)
        FROM fact_booking;
    """)

    count = cursor.fetchone()[0]

    print(f"fact_booking contains {count} records")

    cursor.close()
    connection.close()

# ============================================================
# LOAD DATE DIMENSION
# ============================================================
# UPDATED: now also pulls payment_date and return_date, not just
# booking dates - needed because fact_transactions (new) has rows for
# payments and returns too, and their dates must exist in dim_date for
# the foreign key to be valid.

def load_dim_date():

    connection = psycopg2.connect(**DB_CONFIG)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO dim_date (
            date_key,
            full_date,
            day,
            month,
            month_name,
            quarter,
            year,
            weekday_name
        )

        SELECT DISTINCT

            CAST(TO_CHAR(d, 'YYYYMMDD') AS INTEGER),

            d,

            EXTRACT(DAY FROM d),

            EXTRACT(MONTH FROM d),

            TO_CHAR(d, 'Month'),

            EXTRACT(QUARTER FROM d),

            EXTRACT(YEAR FROM d),

            TO_CHAR(d, 'Day')

        FROM (
            SELECT booking_date AS d FROM bookings
            UNION
            SELECT event_date FROM bookings
            UNION
            SELECT payment_date FROM payments
            UNION
            SELECT return_date FROM returns
        ) dates

        WHERE d IS NOT NULL

        ON CONFLICT (date_key)
        DO NOTHING;
    """)

    connection.commit()

    cursor.execute("SELECT COUNT(*) FROM dim_date;")

    count = cursor.fetchone()[0]

    print(f"dim_date contains {count} records")

    cursor.close()
    connection.close()


# ============================================================
# LOAD FACT_TRANSACTIONS (NEW)
# ============================================================
# The proposal's actual named fact table - one row per individual
# transaction event (a booked item, a payment, or a return), each tied
# to a customer, an inventory item (where applicable), a date, and the
# utterance that produced it.
#
# This does a full DELETE + re-INSERT each run rather than an upsert,
# since a single natural unique key doesn't exist across the three
# different source tables feeding into one fact table. This is fine for
# a manually-triggered DAG on a single pilot store's data volume - for
# a much larger production system, an incremental append-only design
# (never deleting) would be preferable.

def load_fact_transactions():

    connection = psycopg2.connect(**DB_CONFIG)
    cursor = connection.cursor()

    cursor.execute("DELETE FROM fact_transactions;")

    # --- BOOKING_ITEM rows ---
    cursor.execute("""
        INSERT INTO fact_transactions (
            transaction_type, customer_id, item_id, date_key,
            utterance_id, quantity, amount, source_table, source_id
        )
        SELECT
            'BOOKING_ITEM',
            b.customer_id,
            bi.item_id,
            CAST(TO_CHAR(b.event_date, 'YYYYMMDD') AS INTEGER),
            (SELECT MAX(utterance_id) FROM utterance_logs WHERE booking_id = b.booking_id),
            bi.quantity,
            bi.total_price,
            'booking_items',
            bi.booking_item_id
        FROM booking_items bi
        JOIN bookings b ON b.booking_id = bi.booking_id;
    """)

    # --- PAYMENT rows ---
    cursor.execute("""
        INSERT INTO fact_transactions (
            transaction_type, customer_id, item_id, date_key,
            utterance_id, quantity, amount, source_table, source_id
        )
        SELECT
            'PAYMENT',
            b.customer_id,
            NULL,
            CAST(TO_CHAR(p.payment_date, 'YYYYMMDD') AS INTEGER),
            (SELECT MAX(utterance_id) FROM utterance_logs WHERE booking_id = p.booking_id),
            NULL,
            p.amount,
            'payments',
            p.payment_id
        FROM payments p
        JOIN bookings b ON b.booking_id = p.booking_id;
    """)

    # --- RETURN rows ---
    cursor.execute("""
        INSERT INTO fact_transactions (
            transaction_type, customer_id, item_id, date_key,
            utterance_id, quantity, amount, source_table, source_id
        )
        SELECT
            'RETURN',
            b.customer_id,
            NULL,
            CAST(TO_CHAR(r.return_date, 'YYYYMMDD') AS INTEGER),
            (SELECT MAX(utterance_id) FROM utterance_logs WHERE booking_id = r.booking_id),
            r.quantity_returned,
            NULL,
            'returns',
            r.return_id
        FROM returns r
        JOIN bookings b ON b.booking_id = r.booking_id;
    """)

    connection.commit()

    cursor.execute("SELECT COUNT(*) FROM fact_transactions;")
    count = cursor.fetchone()[0]
    print(f"fact_transactions contains {count} records")

    cursor.close()
    connection.close()


# ============================================================
# DAG
# ============================================================

with DAG(
    dag_id="voicebook_etl",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["voicebook", "etl", "warehouse"],
    ) as dag:

    customer_dimension = PythonOperator(
        task_id="load_dim_customer",
        python_callable=load_dim_customer
    )

    inventory_dimension = PythonOperator(
        task_id="load_dim_inventory",
        python_callable=load_dim_inventory
    )

    date_dimension = PythonOperator(
        task_id="load_dim_date",
        python_callable=load_dim_date
    )

    utterance_dimension = PythonOperator(
        task_id="load_dim_utterance",
        python_callable=load_dim_utterance
    )

    booking_fact = PythonOperator(
        task_id="load_fact_booking",
        python_callable=load_fact_booking
    )

    transactions_fact = PythonOperator(
        task_id="load_fact_transactions",
        python_callable=load_fact_transactions
    )

    # All dimensions must load before either fact table, since the fact
    # rows have foreign keys pointing at the dimension tables.
    [customer_dimension, inventory_dimension, date_dimension, utterance_dimension] >> booking_fact
    [customer_dimension, inventory_dimension, date_dimension, utterance_dimension] >> transactions_fact
