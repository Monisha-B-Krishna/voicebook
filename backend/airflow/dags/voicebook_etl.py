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
        ) dates

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

    date_dimension = PythonOperator(
    task_id="load_dim_date",
    python_callable=load_dim_date
    )

    booking_fact = PythonOperator(
    task_id="load_fact_booking",
    python_callable=load_fact_booking
    )

    customer_dimension >> date_dimension >> booking_fact

    