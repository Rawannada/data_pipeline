from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

with DAG(dag_id="taxi_ingest_airflow", start_date=datetime(2021, 1, 1), schedule="@daily") as dag:
    
    def hello():
        print("Hello from Airflow, Rawan!")

    task1 = PythonOperator(
        task_id="say_hello",
        python_callable=hello
    )