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


def get_report_result(plugin, ident, page=1, page_size=20):
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

    original_params = task_group.params.copy() if task_group.params else {}
    current_request_params = {**original_params, 'page': page, 'pageSize': page_size}
    temp_task_params = {'params': current_request_params}

    result = {}
    try:
        if hasattr(plugin, 'raport'):
            result = plugin.raport(temp_task_params)
        else:
            result = generic_get_result(ident)

    except Exception as e:
        import traceback
        traceback.print_exc()
        result = {
            'errors': [f"Błąd podczas generowania strony: {e}"],
            'results': [],
            'actions': [],
            'progress': 1.0,
        }

    if result is None:
        result = {}

    result['progress'] = 1.0

    if 'actions' in result:
        result['actions'] = ReportActions(result['actions'])

    if hasattr(plugin, 'LAUNCH_DIALOG'):
        if task_group is not None and hasattr(task_group, 'params'):
            result['params'] = plugin.LAUNCH_DIALOG.prettify_params(task_group.params)
    
    return result