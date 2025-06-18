import subprocess
import time
import sys
from config import Config
from api.common import get_db
from helpers import divide_chunks

cfg = Config()

SAMODZIELNE_WORKERY = ['ZAWODZI', 'CZERNIA', 'RZESZOW', 'PRZ-PLO', 'LODZ', 'BYDGOW', 'SIEDLCE', 'LUBLIN', 'LUBLINC']


def execute(cmd):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    return out.decode()


def running_screens():
    res = []
    _ = execute(['screen', '-wipe'])
    ls_res = execute(['screen', '-wipe'])
    for line in ls_res.split('\n'):
        if 'repworker-' in line:
            res.append(line.replace('\t', ' ').strip().split(' ')[0])
    return res


def kill_screen(name):
    print('killing screen', name)
    execute(['screen', '-X', '-S', name, 'quit'])


def clear_queue_if_needed(queue):
    if '--clear-queues' not in sys.argv:
        return
    cmd = [cfg.RQ_EXECUTABLE, 'empty', queue]
    execute(cmd)


def start_screen(name, command):
    cmd = ['screen', '-dm', '-S', name]
    if isinstance(command, list):
        for scmd in command:
            cmd.append(scmd)
    else:
        cmd.append(command)
    print('starting screen', name, command)
    execute(cmd)


def start_worker_screen(queue):
    clear_queue_if_needed(queue)
    screen_name = queue.replace('execute/', '').replace('/', '_')
    screen_name = 'repworker-' + screen_name
    screen_name += str(int(time.time() % 100000 ))
    cmd = [cfg.RQ_EXECUTABLE, 'worker', '--with-scheduler', queue]
    cmd += ['-n', screen_name]
    if cfg.SENTRY_URL is not None:
        cmd += ['--sentry-dsn', cfg.SENTRY_URL]
    start_screen(screen_name, cmd)


def start_multiworker_screen(type, prio, targets):
    screen_name = 'repworker-multi-%s_%d_%s' % (type, prio, targets[0])
    screen_name += str(int(time.time() % 100000 ))
    queues = ['execute/%s/%d/%s' % (type, prio, target) for target in targets]
    for queue in queues:
        clear_queue_if_needed(queue)
    cmd = [cfg.RQ_EXECUTABLE, 'worker', '--with-scheduler']
    cmd += ['-n', screen_name]
    if cfg.SENTRY_URL is not None:
        cmd += ['--sentry-dsn', cfg.SENTRY_URL]
    cmd += queues
    start_screen(screen_name, cmd)


if __name__ == '__main__':
    must_wait = False
    for screen in running_screens():
        kill_screen(screen)
        must_wait = True
    if must_wait:
        time.sleep(5)
    centrumy = []
    with get_db() as db:
        for row in db.select('select * from laboratoria'):
            if row['adres'] is not None:
                if row['symbol'] in SAMODZIELNE_WORKERY:
                    start_multiworker_screen('centrum', 0, [row['symbol']])
                    start_multiworker_screen('centrum', 1, [row['symbol']])
                else:
                    centrumy.append(row['symbol'])
    for chunk in divide_chunks(centrumy, 4):
        if 'KOPERNI' in chunk:
            chunk.append('KOPERNIKA')
        start_multiworker_screen('centrum', 0, chunk)
        start_multiworker_screen('centrum', 1, chunk)
        # start_multiworker_screen('centrum', 2, chunk)
    start_worker_screen('execute/snr/0')
    start_worker_screen('execute/snr/1')
    # start_worker_screen('execute/snr/2')
    start_worker_screen('execute/ick/0')
    start_worker_screen('execute/ick/1')
    start_worker_screen('execute/ick/2')
    start_worker_screen('execute/mop/0')
    start_worker_screen('execute/mop/1')
    # start_worker_screen('execute/mop/2')
    start_worker_screen('execute/hbz/0')
    start_worker_screen('execute/hbz/1')
    # start_worker_screen('execute/hbz/2')
    start_worker_screen('execute/noc/0')
    start_worker_screen('execute/noc/1')
    # start_worker_screen('execute/noc/2')
    start_worker_screen('execute/ssh/others')
    start_worker_screen('execute/crm/0')
    start_worker_screen('execute/crm/1')
    start_worker_screen('execute/info/0')
    start_worker_screen('execute/info/1')




