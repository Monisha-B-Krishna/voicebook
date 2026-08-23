from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
import psycopg2


def check_voicebook_database():

    connection = psycopg2.connect(
        host="postgres",
        port=5432,
        database="voicebook",
        user="voicebook",
        password="voicebook_password"
    )

    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM customers;")

    customer_count = cursor.fetchone()[0]

    print(f"VoiceBook customers in PostgreSQL: {customer_count}")

    cursor.close()
    connection.close()


with DAG(
    dag_id="voicebook_db_check",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["voicebook"],
) as dag:

    check_database = PythonOperator(
        task_id="check_voicebook_database",
        python_callable=check_voicebook_database
    )