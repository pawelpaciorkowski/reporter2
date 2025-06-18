import datetime
import json
import traceback

from datasources.reporter import ReporterDatasource
from crontab import CronTab
from dataclasses import dataclass, field

from dialog import ValidationError
from raporty.common import generic_start_report, generic_get_result
from tasks import TaskGroup


@dataclass(frozen=True)
class CronJob:
    id: int
    last_run: datetime.datetime
    name: str
    plugin: str
    params: dict
    schedule: str

    def can_start(self):
        if self.last_run is None:
            return True
        else:
            schedule = CronTab(self.schedule)
            next_run = schedule.next(now=self.last_run, default_utc=False, delta=False, return_datetime=True)
            return next_run <= datetime.datetime.now()

class CronJobManager:
    def __init__(self, plugin_manager):
        self.plugin_manager = plugin_manager
        self.db = ReporterDatasource(read_write=True)
        self.jobs = [CronJob(**row) for row in self.db.dict_select("""
            select pl.id, pl.name, pl.plugin, pl.params, pl.schedule, max(log.started_at) as last_run
            from cron_plan pl
            left join cron_log log on log.cron_plan_id=pl.id
            where pl.is_active
            group by 1, 2, 3, 4
        """)]
        self.pending_tasks = self.db.dict_select("""
            select cl.*, cp.plugin from cron_log cl left join cron_plan cp on cp.id=cl.cron_plan_id
            where cl.finished_at is null""")

    def start_new_jobs(self):
        for job in self.jobs:
            if job.can_start():
                print("Uruchamiam", job.name)
                plugin = self.plugin_manager.find_plugin_by_path(job.plugin)
                try:
                    task_group = plugin.start_report(job.params)
                    # TODO tu się więcej dzieje - logowanie itp, patrz api.report.api; do refaktoryzacji
                    task_group_id = task_group.ident
                    self.db.insert('cron_log', {
                        'cron_plan_id': job.id,
                        'started_at': datetime.datetime.now(),
                        'task_group_id': task_group_id,
                    })
                except ValidationError as e:
                    self.db.insert('cron_log', {
                        'cron_plan_id': job.id,
                        'started_at': datetime.datetime.now(),
                        'finished_at': datetime.datetime.now(),
                        'success': False,
                        'error_log': str(e),
                    })
                except:
                    error = traceback.format_exc()
                    self.db.insert('cron_log', {
                        'cron_plan_id': job.id,
                        'started_at': datetime.datetime.now(),
                        'finished_at': datetime.datetime.now(),
                        'success': False,
                        'error_log': error,
                    })
                self.db.commit()

    def collect_results(self):
        for task in self.pending_tasks:
            plugin = self.plugin_manager.find_plugin_by_path(task['plugin'])
            ident = task['task_group_id']
            try:
                if hasattr(plugin, 'get_result'):
                    result = plugin.get_result(ident)
                else:
                    result = generic_get_result(ident)
            except Exception as e:
                error = traceback.format_exc()
                self.db.update('cron_log', {'id': task['id']}, {
                    'finished_at': datetime.datetime.now(),
                    'success': False,
                    'error_log': error,
                })
                self.db.commit()
                continue
            if result is None:
                result = {}
            results_info = { 'can_open': False, 'can_download': False }
            if 'results' in result:
                for row in result['results']:
                    if row.get('type') == 'download':
                        if 'result_files' not in results_info:
                            results_info['result_files'] = []
                        results_info['result_files'].append(row['filename'])
                    else:
                        results_info['can_open'] = True
                        results_info['can_download'] = True
            # if 'actions' in result:
            #     result['actions'] = ReportActions(result['actions'])
            task_group = TaskGroup.load(ident)
            if hasattr(plugin, 'LAUNCH_DIALOG'):
                if task_group is not None and hasattr(task_group, 'params'):
                    result['params'] = plugin.LAUNCH_DIALOG.prettify_params(task_group.params)
            if task_group.progress == 1.0:
                print("Zbieram wynik", task['plugin'])
                result_id = self.db.insert('cron_results', {'result': json.dumps(result)})
                self.db.update('cron_log', {'id': task['id']}, {
                    'cron_results_id': result_id,
                    'finished_at': datetime.datetime.now(),
                    'success': True, # TODO - rozpoznawanie porażki na wyjątkach
                    'results_info': json.dumps(results_info)
                })
                self.db.commit()



"""

create table cron_plan (
	id serial primary key,
	name varchar(256),
	schedule varchar(128),
	plugin varchar(128),
	params jsonb,
	users text,
	is_active boolean
);

create table cron_log (
	id serial primary key,
	cron_plan_id bigint,
	cron_results_id bigint,
	started_at timestamp without time zone,
	finished_at timestamp without time zone,
	task_group_id varchar(64),
	success boolean,
	error_log text
);

create index on cron_log(cron_plan_id, started_at);

create table cron_results (
	id serial primary key,
	result text
);

"""
