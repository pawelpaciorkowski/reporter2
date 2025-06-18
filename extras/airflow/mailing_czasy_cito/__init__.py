import yaml
import airflow
from airflow import DAG
from datetime import datetime, timedelta, time
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator
from datetime import datetime

import os
import re
import unidecode

def slugify(text):
    text = unidecode.unidecode(text).lower()
    return re.sub(r'[\W_]+', '-', text)


dag = DAG(
    'mailing_czasy_cito',
    description='Mailowa wysyłka raportów o przekroczeniu czasów cito',
    schedule_interval='30 4 * * *',
    start_date=datetime.strptime('2023-12-14', '%Y-%m-%d')
)

def utworz_wezel_raportu(wiersz):
    global dag
    command = "cd /home/centrum-system/airflow/dags/mailing_czasy_cito ; "
    command += "export PYTHONPATH=/home/centrum-system/raporty_python_lib/ ; "
    command += "/home/centrum-system/.virtualenvs/reporter/bin/python czasy_cito.py"
    command += ' "%s"' % wiersz['nazwa']
    command += ' "%s"' % wiersz['vpn']
    command += ' "%s"' % wiersz['baza']
    command += ' "%s"' % wiersz['emaile']
    res = BashOperator(
        task_id=slugify(wiersz['nazwa']), 
        dag=dag,
        execution_timeout=timedelta(hours=1),
        retries=3,
        retry_timeout=timedelta(hours=3),
        bash_command=command
    )
    return res

start = DummyOperator(
    task_id='start',
    dag=dag
)

end = DummyOperator(
    task_id='end',
    dag=dag
)

with open(os.path.abspath(os.path.dirname(__file__)) + '/konfiguracja.yml') as f:
    cfg = yaml.safe_load(f)
    for row in cfg['instancje']:
        oper = utworz_wezel_raportu(row)
        start >> oper
        oper >> end

