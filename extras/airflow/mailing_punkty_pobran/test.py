import yaml
# import airflow
# from airflow import DAG
from datetime import datetime, timedelta, time
from datetime import datetime

import os
import re




def utworz_wezel_raportu(wiersz):
    command = "cd /home/centrum-system/airflow/dags/mailing_punkty_pobran ; "
    command += "export PYTHONPATH=/home/centrum-system/raporty_python_lib/ ; "
    command += "/home/centrum-system/.virtualenvs/reporter/bin/python punkty_pobran.py"
    command += ' "%s"' % wiersz['symbol']
    command += ' "%s"' % wiersz['nazwa'].replace('"', '').replace('\n', ' ')
    command += ' "%s"' % wiersz['vpn']
    command += ' "%s"' % wiersz['baza']
    command += ' "%s"' % wiersz['emaile']
    print(command)

with open(os.path.abspath(os.path.dirname(__file__)) + '/konfiguracja.yml') as f:
    cfg = yaml.safe_load(f)
    for row in cfg['instancje']:
        oper = utworz_wezel_raportu(row)

