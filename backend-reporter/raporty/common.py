from tasks import TaskGroup, Task
from raporty.actions import ReportActions


def generic_start_report(plugin, params):
    pass


def generic_get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return {
            'errors': [
                'Nie znaleziono TaskGroup - raport anulowany lub brak TaskGroup.save()?'
            ],
            'results': [],
            'actions': [],
            'progress': 1.0,
        }
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx']
    }
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            if isinstance(result, list):
                for subres in result:
                    res['results'].append(subres)
            elif isinstance(result, dict) and 'results' in result:
                res = result
                if 'errors' not in res:
                    res['errors'] = []
            else:
                res['results'].append(result)
        if status == 'failed':
            if 'target' in params:
                res['errors'].append('%s - błąd połączenia' % params['target'])
            else:
                res['errors'].append('Błąd połączenia')
    res['progress'] = task_group.progress
    return res


def get_report_result(plugin, ident):
    if hasattr(plugin, 'get_result'):
        result = plugin.get_result(ident)
    else:
        result = generic_get_result(ident)
    if result is None:
        result = {}
    if 'actions' in result:
        result['actions'] = ReportActions(result['actions'])
    if hasattr(plugin, 'LAUNCH_DIALOG'):
        task_group = TaskGroup.load(ident)
        if task_group is not None and hasattr(task_group, 'params'):
            result['params'] = plugin.LAUNCH_DIALOG.prettify_params(task_group.params)
    return result