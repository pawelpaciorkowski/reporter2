"""
wypisanie aktualnej zawartości screena do pliku:
screen -S repworker-ick_1 -X hardcopy /tmp/screen-hardcopy

"""

import pickle
from helpers import prepare_for_json, TrustedAction
from rq.cli.helpers import CliConfig
from tasks.db import redis_url, redis_conn

import subprocess
# TODO: odpalanie komend przenieść gdzieś do helpera

MENU_ENTRY='Procesy zbierające'

REQUIRE_ROLE = ['C-CS']
GUI_MODE = 'one_shot'


class ViewWorkerScreen(TrustedAction):
    params_available = ['worker']

    def execute(self):
        # TODO XXX - sprawdzić czy istnieje taki worker!
        cmd = ['screen', '-S', self.params['worker'], '-X', 'hardcopy', '/tmp/screen-hardcopy']
        proc = subprocess.Popen(cmd)
        proc.communicate()
        with open('/tmp/screen-hardcopy', 'r') as f:
            return f.read()


def get_content(user_login):
    tables = []

    cli_config = CliConfig()

    for worker in cli_config.worker_class.all(connection=redis_conn):
        data = []
        for queue in worker.queues:
            wiersz = [queue.name.replace('execute/', '')]
            if len(queue) > 0:
                wiersz.append({'value': len(queue), 'background': 'yellow'})
                job = queue.get_jobs(0, 1)[0]
                wiersz.append(job.id)
                wiersz.append(job.enqueued_at)
                wiersz.append(job.started_at)
                params = pickle.loads(job.data)[2]
                wiersz.append(params[0]['plugin'])
                wiersz.append('')  # TODO: aktualnie w tasku nie mamy użytkownika
            else:
                wiersz += [0, '', '', '', '', '']
            data.append(wiersz)
        data.sort(key=lambda row: ('AAA' if isinstance(row[1], dict) else 'ZZZ') + row[0])
        tables.append({
            'type': 'action',
            'subtype': 'popup_view',
            'title': worker.name,
            'icon': 'cog',
            'token': ViewWorkerScreen(worker=worker.name).get_token(),
        })
        tables.append({
            'type': 'table',
            'header': ['Kolejka', 'Ilość zadań', 'Bieżące zadanie', 'B.z. zakolejkowane', 'B.z. uruchomione', 'B.z. raport', 'B.z. użytkownik'],
            'data': prepare_for_json(data)
        })
    return tables
