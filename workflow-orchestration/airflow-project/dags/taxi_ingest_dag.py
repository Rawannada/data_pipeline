from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime
import pandas as pd
import os

default_args = {
    'owner': 'rawan',
    'start_date': datetime(2020, 1, 1),
    'end_date': datetime(2020, 12, 31),
}

def ingest_callable(csv_file, table_name, taxi_type):
    hook = PostgresHook(postgres_conn_id='pg_taxi_db')
    engine = hook.get_sqlalchemy_engine()
    
    pickup_col = 'tpep_pickup_datetime' if taxi_type == 'yellow' else 'lpep_pickup_datetime'
    dropoff_col = 'tpep_dropoff_datetime' if taxi_type == 'yellow' else 'lpep_dropoff_datetime'
    
    # التأكد من وجود الملف قبل القراءة
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"الملف {csv_file} غير موجود!")

    df_iter = pd.read_csv(csv_file, iterator=True, chunksize=100000, low_memory=False)
    
    for chunk in df_iter:
        chunk[pickup_col] = pd.to_datetime(chunk[pickup_col])
        chunk[dropoff_col] = pd.to_datetime(chunk[dropoff_col])
        chunk.to_sql(name=table_name, con=engine, if_exists='append', index=False)
        print(f"Inserted a chunk into {table_name}...")
    
    # خطوة اختيارية: حذف الملف بعد الرفع لتوفير المساحة
    os.remove(csv_file)
    print(f"Removed temporary file: {csv_file}")

with DAG(
    dag_id='nyc_taxi_bulk_2020_v3', # غيرت الاسم لتبدأ نسخة نظيفة
    default_args=default_args,
    schedule_interval='@monthly',
    catchup=True,
    max_active_runs=1 # تقليل العدد لضمان عدم توقف الجهاز
) as dag:

    for taxi in ['yellow', 'green']:
        # استخدام logical_date بدلاً من execution_date
        DATE_STR = "{{ logical_date.strftime('%Y-%m') }}"
        URL_TEMPLATE = f"https://github.com/DataTalksClub/nyc-tlc-data/releases/download/{taxi}/{taxi}_tripdata_{DATE_STR}.csv.gz"
        RAW_FILE = f"/tmp/{taxi}_data_{DATE_STR}.csv.gz"
        UNZIPPED_FILE = f"/tmp/{taxi}_data_{DATE_STR}.csv"
        TABLE_NAME = f"{taxi}_taxi_2020"

        download_task = BashOperator(
            task_id=f'download_{taxi}_csv',
            bash_command=f'curl -sSL {URL_TEMPLATE} > {RAW_FILE}'
        )

        unzip_task = BashOperator(
            task_id=f'unzip_{taxi}_csv',
            bash_command=f'gunzip -f {RAW_FILE}'
        )

        ingest_task = PythonOperator(
            task_id=f'ingest_{taxi}_to_postgres',
            python_callable=ingest_callable,
            op_kwargs={
                'csv_file': UNZIPPED_FILE,
                'table_name': TABLE_NAME,
                'taxi_type': taxi
            }
        )

        download_task >> unzip_task >> ingest_task