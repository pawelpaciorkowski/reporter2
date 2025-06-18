import datetime
import time
from sentry_sdk import configure_scope
from datasources.centrum import CentrumConnectionError
from .db import redis_conn
from rq import Queue
from plugins import PluginManager
from uuid import uuid4

class TaskKillMonitor:
    def __init__(self, job_id):
        self.job_id = job_id
        self.is_monitoring = True
        self.task_start = time.perf_counter()

    def __enter__(self):
        print('Start monitoring', self.job_id)

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.task_start
        print('End monitoring', self.job_id, duration)

    def monitor_task(self):
        while self.is_monitoring:
            pass


class Task:
    def __init__(self, task_group, params):
        self.job_id = None
        priority = int(params.get('priority', 1))
        self.queue = None
        if params['type'] == 'centrum':
            self.queue = 'execute/centrum/%d/%s' % (priority, params['target'])
        if params['type'] == 'snr':
            self.queue = 'execute/snr/%d' % priority
        if params['type'] == 'ick':
            self.queue = 'execute/ick/%d' % priority
        if params['type'] == 'mop':
            self.queue = 'execute/mop/%d' % priority
        if params['type'] == 'hbz':
            self.queue = 'execute/hbz/%d' % priority
        if params['type'] == 'noc':
            self.queue = 'execute/noc/%d' % priority
        if params['type'] == 'ssh':
            self.queue = 'execute/ssh/%s' % params['target']
        self.job_timeout = params.get('timeout', [30, 300, 1200][priority])
        if self.queue is not None:
            self.job_id = str(uuid4())
            params['job_id'] = self.job_id
            q = Queue(self.queue, connection=redis_conn)
            job = q.enqueue(self.do_task_work, params, result_ttl=86400, job_timeout=self.job_timeout)
            self.job_id = job.id

    @classmethod
    def load(cls, ident):
        pass

    def save(self):
        pass

    def do_task_work(self, params):
        # TODO: try / except z raportowaniem
        def retry_after_fail(base_delay=1):
            if 'retries' not in params:
                return
            if params['retries'] == 0:
                return
            params['retries'] -= 1
            if '_retry' not in params:
                params['_retry'] = 0
            else:
                params['_retry'] += 1
            delay = base_delay * (2 ** params['_retry']) * datetime.timedelta(seconds=1)
            print('Nie poszło. %d próba za %d seconds' % (params['_retry'], delay.total_seconds()))
            q = Queue(self.queue, connection=redis_conn)
            job = q.enqueue_in(delay, self.do_task_work, params, result_ttl=86400, job_timeout=self.job_timeout)
            print(job)

        with configure_scope() as scope:
            scope.set_context('task_params', params)
            scope.set_context('queue', self.queue)
            with TaskKillMonitor(params['job_id']):
                pm = PluginManager(lazy=True)
                plugin = pm.find_plugin_by_path(params['plugin'])
                perform = getattr(plugin, params['function'])
                try:
                    return perform(params)
                except CentrumConnectionError as e:
                    if e.variant in (0, 1):
                        scope.set_context('error_type', 'CentrumConnectionError')
                        scope.set_context('centrum_system', e.system)
                    retry_after_fail(60)
                    raise e
                except Exception as e:
                    retry_after_fail(10)
                    raise e

    @property
    def ident(self):
        # jeśli niezapisane to zapisać, zwrócić self.ident
        return self.ident

    def save_data_chunk(self, subident, data):
        pass

    def get_data_chunk(self, subident):
        pass

    def get_data(self):
        pass


class TaskResult:
    def __init__(self, task):
        print('TaskResult init')

    @classmethod
    def load(cls, ident):
        pass

    def save(self):
        pass

    @property
    def ident(self):
        # jeśli niezapisane to zapisać, zwrócić self.ident
        return self.ident
