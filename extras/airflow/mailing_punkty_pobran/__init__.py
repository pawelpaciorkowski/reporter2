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
    'mailing_punkty_pobran',
    description='Mailowa wysyłka raportów niezgodności dla punktów pobrań',
    schedule_interval='10 6 * * *',
    start_date=datetime.strptime('2023-12-14', '%Y-%m-%d')
)

def utworz_wezel_raportu(wiersz):
    global dag
    command = "cd /home/centrum-system/airflow/dags/mailing_punkty_pobran ; "
    command += "export PYTHONPATH=/home/centrum-system/raporty_python_lib/ ; "
    command += "/home/centrum-system/.virtualenvs/reporter/bin/python punkty_pobran.py"
    command += ' "%s"' % wiersz['symbol']
    command += ' "%s"' % wiersz['nazwa'].replace('"', '').replace('\n', ' ')
    command += ' "%s"' % wiersz['vpn']
    command += ' "%s"' % wiersz['baza']
    command += ' "%s"' % wiersz['emaile']
    res = BashOperator(
        task_id=slugify('%s %s' % (wiersz['symbol'], wiersz['nazwa'])),
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

