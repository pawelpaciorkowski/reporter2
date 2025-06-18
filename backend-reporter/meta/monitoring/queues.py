import pickle
from helpers import prepare_for_json
from plugins import ROLE_CONTAINMENT
from api.common import get_db
from api.restplus import api
from rq.cli.helpers import CliConfig
from tasks.db import redis_url, redis_conn

MENU_ENTRY = 'Kolejki'

REQUIRE_ROLE = ['C-CS']
GUI_MODE = 'one_shot'

def get_content(user_login):
    data = []

    cli_config = CliConfig()

    for queue in cli_config.queue_class.all(connection=redis_conn):
        wiersz = [queue.name.replace('execute/', '')]
        if len(queue) > 0:
            wiersz.append({'value': len(queue), 'background': 'yellow'})
            job = queue.get_jobs(0, 1)[0]
            wiersz.append(job.id)
            wiersz.append(job.enqueued_at)
            wiersz.append(job.started_at)
            params = pickle.loads(job.data)[2]
            wiersz.append(params[0]['plugin'])
            wiersz.append('') # TODO: aktualnie w tasku nie mamy użytkownika
        else:
            wiersz += [0, '', '', '', '', '']
        data.append(wiersz)
    data.sort(key=lambda row: ('AAA' if isinstance(row[1], dict) else 'ZZZ') + row[0])
    # queue.empty() - TODO XXX - tak można opróżnić kolejkę w razie potrzeby
    return [
        {
            'type': 'table',
            'title': 'Kolejki',
            'header': ['Kolejka', 'Ilość zadań', 'Bieżące zadanie', 'B.z. zakolejkowane', 'B.z. uruchomione', 'B.z. raport', 'B.z. użytkownik'],
            'data': prepare_for_json(data)
        }
    ]
