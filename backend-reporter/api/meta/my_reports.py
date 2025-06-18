import json
from api.restplus import api
from flask_restx import Resource

from api.restplus import api
from datasources.reporter import ReporterDatasource
from helpers import prepare_for_json, slugify
from .api import ns
from ..auth.utils import login_required
from raporty.actions import ReportActionExecutor, ReportActions


class MyReportsResource(Resource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rep = ReporterDatasource()
        self.plugin_titles = {}

    def get_plugin_title(self, path):
        if path not in self.plugin_titles:
            title = None
            plugin = api.plugin_manager.find_plugin_by_path(path)
            if hasattr(plugin, 'LAUNCH_DIALOG'):
                try:
                    title = plugin.LAUNCH_DIALOG.init_kwargs['title']
                except:
                    pass
            if title is None and hasattr(plugin, 'MENU_ENTRY'):
                title = plugin.MENU_ENTRY
            self.plugin_titles[path] = title
        return self.plugin_titles.get(path)

    def get_plan_for_user(self, user_login):
        res = {}
        for plan_row in self.rep.dict_select("select * from cron_plan where users like %s",
                                             ['%' + user_login + '%']):
            if ' %s ' % user_login in ' %s ' % plan_row['users']:
                plan_row['report_title'] = self.get_plugin_title(plan_row['plugin'])
                res[plan_row['id']] = plan_row
        return res


@ns.route('/myReports/forDay/<string:date>')
class MyReportsForDay(MyReportsResource):
    @login_required
    def get(self, date, user_login, user_permissions):
        reports = []
        for plan_id, plan_row in self.get_plan_for_user(user_login).items():
            for log_row in self.rep.dict_select(
                    "select * from cron_log where cron_plan_id=%s and cast(started_at as date)=%s", [plan_id, date]):
                log_row['plan'] = plan_row
                reports.append(log_row)
        return {
            'date': date,
            'reports': prepare_for_json(reports),
        }


@ns.route('/myReports/job/<int:id>/<int:page>')
class MyReportsSingle(MyReportsResource):
    results_per_page = 10

    @login_required
    def get(self, id, page, user_login, user_permissions):
        plan = self.get_plan_for_user(user_login)
        if id not in plan:
            api.abort(404)
        res = plan[id]
        total_count = 0
        for row in self.rep.dict_select("select count(id) as cnt from cron_log where cron_plan_id=%s", [id]):
            total_count = row['cnt']
        page_count = int((total_count + self.results_per_page - 1) / self.results_per_page)
        if page >= page_count:
            page = page_count - 1
        res['page'] = page
        res['page_count'] = page_count
        if total_count > 0:
            res['results'] = self.rep.dict_select("""
                select * from cron_log where cron_plan_id=%s order by id desc limit %s offset %s
            """, [id, self.results_per_page, page * self.results_per_page])
        else:
            res['results'] = []
        return prepare_for_json(res)


@ns.route('/myReports/results/<int:id>')
class MyReportsGetResults(MyReportsResource):
    @login_required
    def get(self, id, user_login, user_permissions):
        plan = self.get_plan_for_user(user_login)
        for log_row in self.rep.dict_select("select * from cron_log where id=%s", [id]):
            if log_row['cron_plan_id'] in plan:
                for res_row in self.rep.dict_select("select * from cron_results where id=%s",
                                                    [log_row['cron_results_id']]):
                    return prepare_for_json(json.loads(res_row['result']))
            else:
                api.abort(403)
        api.abort(404)


@ns.route('/myReports/download/<int:id>')
class MyReportsDownloadResults(MyReportsResource):
    @login_required
    def get(self, id, user_login, user_permissions):
        plan = self.get_plan_for_user(user_login)
        for log_row in self.rep.dict_select("select * from cron_log where id=%s", [id]):
            if log_row['cron_plan_id'] in plan:
                cron_plan = plan[log_row['cron_plan_id']]
                for res_row in self.rep.dict_select("select * from cron_results where id=%s",
                                                    [log_row['cron_results_id']]):
                    result = json.loads(res_row['result'])
                    plugin = api.plugin_manager.find_plugin_by_path(cron_plan['plugin'])
                    report_actions = ReportActions(result.get('actions', []))
                    default_action = None
                    for i, action in enumerate(result.get('actions', [])):
                        if isinstance(action, dict) and action.get('flat_table'):
                            default_action = i
                    for i, action in enumerate(result.get('actions', [])):
                        if default_action is not None and default_action != i:
                            continue
                        action_type = action if isinstance(action, str) else action['type']
                        rae = report_actions.get_action_executor(action_type, i)
                        res = rae.execute(plugin, result, fn_prefix=slugify(cron_plan['name']),
                                          timestamp=log_row['finished_at'])
                        if res is not None:
                            res['status'] = 'ok'
                            return res
                    return {
                        'status': 'error',
                        'error': 'Brak akcji do pobrania.',
                    }
            else:
                api.abort(403)
        api.abort(404)


@ns.route('/myReports/downloadFile/<int:id>/<int:file_idx>')
class MyReportsDownloadResultFile(MyReportsResource):
    @login_required
    def get(self, id, file_idx, user_login, user_permissions):
        plan = self.get_plan_for_user(user_login)
        for log_row in self.rep.dict_select("select * from cron_log where id=%s", [id]):
            if log_row['cron_plan_id'] in plan:
                cron_plan = plan[log_row['cron_plan_id']]
                for res_row in self.rep.dict_select("select * from cron_results where id=%s",
                                                    [log_row['cron_results_id']]):
                    result = json.loads(res_row['result'])
                    file_cnt = 0
                    for res in result['results']:
                        if res.get('type') == 'download':
                            if file_cnt == file_idx:
                                return {
                                    'status': 'ok',
                                    'content': res['content'],
                                    'content_type': res['content_type'],
                                    'filename': res['filename'],
                                }
                            file_cnt += 1
                    return {
                        'status': 'error',
                        'error': 'Brak pliku do pobrania.',
                    }
            else:
                api.abort(403)
        api.abort(404)
