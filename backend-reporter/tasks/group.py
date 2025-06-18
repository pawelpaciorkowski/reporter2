from .task import Task
import uuid
from . import db
from api.common import get_db
import json


class TaskGroup:
    def __init__(self, plugin, params):
        self.plugin = plugin
        self.params = params
        self.ident = str(uuid.uuid4())
        self.tasks = []
        self.additional_info = {}
        self.computed_progress = None

    def create_task(self, task_params):
        task_params['plugin'] = self.plugin
        task_params['task_group_id'] = self.ident
        task = Task(self, task_params)
        self.tasks.append([task.job_id, task_params])
        return task

    def set_additional_info(self, **kwargs):
        for k, v in kwargs.items():
            self.additional_info[k] = v

    @classmethod
    def load(cls, ident):
        val = db.load_task_group(ident)
        if val is None:
            return None
        res = TaskGroup(None, None)
        res.ident = ident
        res.plugin = val['plugin']
        res.params = val['params']
        res.tasks = val['tasks']
        return res

    @property
    def progress(self):
        if self.computed_progress is None:
            self.get_tasks_results()
        return self.computed_progress

    def save(self):
        db.save_task_group(self.ident, {
            'plugin': self.plugin,
            'params': self.params,
            'tasks': self.tasks
        })

    def log_event(self, user_id, event_type):
        parametry = {
            'params': self.params,
            'ident': self.ident,
        }
        if len(self.additional_info.keys()) > 0:
            parametry['additional_info'] = self.additional_info
        with get_db() as rep_db:
            rep_db.execute("""
                insert into log_zdarzenia(obj_type, obj_id, typ, opis, parametry)
                values('osoba', %s, %s, %s, %s)
            """, [
                user_id, event_type, self.plugin, json.dumps(parametry)
            ])


    def get_tasks_results(self):
        res = []
        all_tasks = 0
        finished_tasks = 0
        successfull_tasks = 0
        for job_id, task_params in self.tasks:
            all_tasks += 1
            job = db.fetch_job(job_id)
            if job is not None:
                status = job.get_status()
                result = job.result
                res.append([job_id, task_params, status, result])
                if status in ['finished', 'failed']: # TODO: failed, canceled, ...
                    finished_tasks += 1
                    if status == 'finished' and result is not None: # TODO: dodatkowe sprawdzenie
                        successfull_tasks += 1
            else:
                res.append([job_id, task_params, 'not found', None])
                finished_tasks += 1
        self.computed_progress = finished_tasks / all_tasks
        return res


