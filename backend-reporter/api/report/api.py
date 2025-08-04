import inspect

import jwt
from api.restplus import api
from dialog import ValidationError
from raporty.common import generic_start_report, generic_get_result, get_report_result
from flask import request, abort, current_app
from flask_restx import Resource, fields, reqparse, inputs
from tasks import TaskGroup
from ..auth.utils import login_required, get_jwt, check_password, encrypt_password
from ..common import get_db
from ..common.resource import APIResource

ns = api.namespace('report', description="Uruchamianie raportów i przeglądanie wyników")


class ReportResource(APIResource):
    def check_permissions(self, plugin, user_login, user_permissions):
        # # TODO: nie ma sprawdzania zasięgu
        for perm_name, perm_range in user_permissions:
            if api.plugin_manager.can_access(perm_name, plugin.__PLUGIN__):
                return True
        api.abort(401, 'Brak dostępu')

    def get_plugin_for_report_type(self, report_type):
        return api.plugin_manager.find_plugin_by_path(report_type)


@ns.route('/for_user/<int:owner>')
class UserReports(ReportResource):
    @login_required
    def get(self, owner, user_login, user_permissions):
        self.check_permissions(None, user_login, user_permissions)


def check_user_quota(user_id, user_permissions):
    if isinstance(user_permissions, list):
        for perm in user_permissions:
            if perm[0] == 'ADMIN':
                return None
    with get_db() as rep_db:
        repgen = repview = 0
        for row in rep_db.select("""select distinct typ, opis, parametry->>'ident', (parametry->'params')::text
                from log_zdarzenia 
                where obj_id=%s and typ in ('REPGEN', 'REPVIEW') and ts >= NOW() - INTERVAL '1 hour'""", [user_id]):
            if row['typ'] == 'REPGEN':
                repgen += 1
            if row['typ'] == 'REPVIEW':
                repview += 1
        if repgen - repview >= 999:
            return 'W ciągu ostatniej godziny uruchomiłeś 3 raporty bez czekania na wynik. Nie można uruchomić raportu.'
        return None

@ns.route('/start/<string:report_type>')
class ReportStart(ReportResource):
    @login_required
    def post(self, report_type, user_id, user_login, user_permissions, user_labs_available):
        user_quota_status = check_user_quota(user_id, user_permissions)
        if user_quota_status is not None:
            return {'error': user_quota_status}
        plugin = self.get_plugin_for_report_type(report_type)
        if plugin is None:
            raise Exception('Nie znaleziono pluginu', report_type)
        self.check_permissions(plugin, user_login, user_permissions)
        params = request.json
        if hasattr(plugin, 'start_report'):
            start_report_fn = plugin.start_report
            fn_params = []
            for arg in inspect.getargs(start_report_fn.__code__).args:
                if arg == 'params':
                    fn_params.append(params)
                elif arg == 'user_login':
                    fn_params.append(user_login)
                elif arg == 'user_permissions':
                    fn_params.append(user_permissions)
                elif arg == 'user_labs_available':
                    fn_params.append(user_labs_available)
        else:
            start_report_fn = generic_start_report
            fn_params = [plugin, params]
        try:
            task_group = start_report_fn(*fn_params)
            if request.headers.get("X-Real-Ip"):
                ip = request.headers.get("X-Real-Ip")
            else:
                ip = request.remote_addr
            task_group.set_additional_info(user_agent=request.headers.get('User-Agent'),
                                           ip=ip, host=request.headers.get('Host'))
            task_group.log_event(user_id, 'REPGEN')
            return {'ident': task_group.ident}
        except ValidationError as e:
            return {'error': ' '.join(e.args)}


# @ns.route('/status/<string:report_type>/<string:ident>')
# class ReportStatus(ReportResource):
#     @login_required
#     def get(self, report_type, ident, user_login, user_permissions):
#         self.check_permissions(report_type, user_login, user_permissions)
#
#     @login_required
#     def post(self, report_type, ident, user_login, user_permissions):
#         """Np anulowanie itp"""
#         self.check_permissions(report_type, user_login, user_permissions)
#
#
# @ns.route('/wait/<string:report_type>/<string:ident>')
# class ReportWaitForCompletion(ReportResource):
#     @login_required
#     def get(self, report_type, ident, user_login, user_permissions):
#         self.check_permissions(report_type, user_login, user_permissions)
#         # TODO: tu jakiś yieldzik by się przydał


@ns.route('/result/<string:report_type>/<string:ident>')
class ReportResult(ReportResource):
    def filter_out_results(self, results):
        res = []
        for elem in results:
            if isinstance(elem, dict):
                if elem.get('type') in ('table', 'vertTable', 'diagram', 'html'):
                    continue
            res.append(elem)
        return res

    # TODO XXX - sprawdzać właściciela raportu
    @login_required
    def get(self, report_type, ident, user_id, user_login, user_permissions):
        show_partial_results = request.args.get('show_partial_results', '0') == '1'
        without_results = request.args.get('results', '1') == '0'
        plugin = self.get_plugin_for_report_type(report_type)
        if plugin is None:
            raise Exception('Nie znaleziono pluginu', report_type)
        self.check_permissions(plugin, user_login, user_permissions)
        task_group = TaskGroup.load(ident)
        if task_group is not None and not show_partial_results:
            if task_group.progress < 1.0:
                return {
                    'progress': task_group.progress, 'errors': [], 'results': [],
                }
        result = get_report_result(plugin, ident)
        if result.get('progress', 0) == 1 and task_group is not None:
            task_group.log_event(user_id, 'REPVIEW')
        if 'actions' in result:
            result['actions'] = result['actions'].get_augmented_actions()
        if 'results' in result and without_results:
            result['results'] = self.filter_out_results(result['results'])
        return result


@ns.route('/action/<string:report_type>/<string:ident>/<string:action_type>/<int:action_index>')
class ReportAction(ReportResource):
    # TODO XXX - sprawdzać właściciela raportu
    @login_required
    def get(self, report_type, ident, action_type, action_index, user_login, user_permissions):
        plugin = self.get_plugin_for_report_type(report_type)
        if plugin is None:
            raise Exception('Nie znaleziono pluginu', report_type)
        self.check_permissions(plugin, user_login, user_permissions)
        result = get_report_result(plugin, ident)
        if 'actions' in result:
            # Sprawdź czy actions jest już obiektem ReportActions
            if isinstance(result['actions'], list):
                from raporty.actions import ReportActions
                result['actions'] = ReportActions(result['actions'])
            executor = result['actions'].get_action_executor(action_type, action_index)
            if executor is not None:
                res = executor.execute(plugin, result)
                return {'status': 'ok', 'result': res}
        return {'status': 'error', 'error': 'Nie można wykonać akcji'}
    

    
    def options(self, report_type, ident, action_type, action_index):
        """Obsługa preflight request dla CORS"""
        from flask import make_response
        response = make_response({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    @login_required
    def post(self, report_type, ident, action_type, action_index, user_login, user_permissions):
        """Obsługa akcji z danymi z formularza"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: POST action - report_type: {report_type}, ident: {ident}, action_type: {action_type}, action_index: {action_index}")
        print(f"DEBUG: POST action - report_type: {report_type}, ident: {ident}, action_type: {action_type}, action_index: {action_index}")
        
        try:
            plugin = self.get_plugin_for_report_type(report_type)
            if plugin is None:
                print(f"ERROR: Nie znaleziono pluginu {report_type}")
                raise Exception('Nie znaleziono pluginu', report_type)
            
            print(f"DEBUG: Plugin found: {plugin}")
            self.check_permissions(plugin, user_login, user_permissions)
            
            # Pobierz dane z formularza
            form_data = request.json or {}
            print(f"DEBUG: POST action - form_data: {form_data}")
            
            print(f"DEBUG: Getting report result for {ident}")
            result = get_report_result(plugin, ident)
            print(f"DEBUG: Report result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            print(f"DEBUG: Report result full: {result}")
            print(f"DEBUG: Report result type: {type(result)}")
            
            if 'actions' in result:
                print(f"DEBUG: Actions found in result")
                # Sprawdź czy actions jest już obiektem ReportActions
                if isinstance(result['actions'], list):
                    print(f"DEBUG: Converting actions list to ReportActions object")
                    from raporty.actions import ReportActions
                    result['actions'] = ReportActions(result['actions'])
                
                print(f"DEBUG: Getting action executor for {action_type}, index {action_index}")
                executor = result['actions'].get_action_executor(action_type, action_index)
                if executor is not None:
                    print(f"DEBUG: Executor found, executing...")
                    # Przekaż dane z formularza do executor
                    res = executor.execute(plugin, result, form_data=form_data)
                    print(f"DEBUG: Execution successful, returning result")
                    
                    # Dodaj nagłówki CORS do odpowiedzi
                    from flask import make_response
                    response = make_response({'status': 'ok', 'result': res})
                    response.headers['Access-Control-Allow-Origin'] = '*'
                    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                    return response
                else:
                    print(f"ERROR: Executor not found for {action_type}, index {action_index}")
            else:
                print(f"ERROR: No actions found in result")
            
            # Dodaj nagłówki CORS do odpowiedzi błędu
            from flask import make_response
            response = make_response({'status': 'error', 'error': 'Nie można wykonać akcji'})
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
            
        except Exception as e:
            print(f"ERROR: Exception in POST action: {e}")
            import traceback
            traceback.print_exc()
            
            # Dodaj nagłówki CORS do odpowiedzi błędu
            from flask import make_response
            response = make_response({'status': 'error', 'error': str(e)})
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
