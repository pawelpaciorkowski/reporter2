import inspect

import jwt
from api.restplus import api
from flask import request, abort, current_app
from flask_restx import Resource, fields, reqparse, inputs

from dialog import ValidationError
from ..auth.utils import login_required, get_jwt, check_password, encrypt_password
from ..common import get_db
from helpers import TrustedAction
from ..common.resource import APIResource

ns = api.namespace('gui', description="Struktury danych opisujące wygląd aplikacji dla zalogowanego użytkownika")

@ns.route('/start')
class StartPageData(Resource):
    @login_required
    def get(self, user_login, user_permissions):
        res = {}
        res['news'] = api.plugin_manager.get_news_for_user('', user_permissions)
        return res


@ns.route('/menu')
class MenuDefinition(Resource):
    def build_menu_for_gui(self, menu):
        if isinstance(menu, list):
            return [self.build_menu_for_gui(item) for item in menu if item.get('menu_entry') is not None]
        else:
            res = {
                'id': self.next_id
            }
            self.next_id += 1
            if 'path' in menu:
                res['url'] = '/' + menu['path']
            if 'menu_entry' in menu:
                me = menu['menu_entry']
                if isinstance(me, str):
                    res['label'] = me
                else:
                    pass  # TODO: bardziej skomplikowane strukturki opisujące menuitem, gdyby miało tu coś dojść to do zmiany wykluczenie na górze tej funkcji
            if 'lazyChildren' in menu:
                res['hasCaret'] = True
                res['lazyLoad'] = True
                res['datasource'] = menu['lazyChildren']
            if 'children' in menu:
                res['childNodes'] = self.build_menu_for_gui(menu['children'])
            return res

    @login_required
    def get(self, user_login, user_permissions):
        menu = api.plugin_manager.get_menu_for_user(user_permissions)
        self.next_id = 1
        return self.build_menu_for_gui(menu)


@ns.route('/menu/sub/<string:ident>')
class SubMenuDefinition(Resource):
    @login_required
    def get(self, ident):
        [submenu_type, path] = ident.split(':')
        if submenu_type == 'submenu':
            return api.plugin_manager.get_submenu_for_user(path)
        return None


def call_with_optional_params(fn, params):
    fn_args = inspect.getargs(fn.__code__).args
    kwargs = {}
    for k, v in params.items():
        if k in fn_args:
            kwargs[k] = v
    return fn(**kwargs)


@ns.route('/page/<string:ident>')
class PageDefinition(APIResource):
    @login_required
    def get(self, ident, user_login, user_permissions):
        plugin = api.plugin_manager.find_plugin_by_path(ident)
        self.check_permissions(plugin, user_login, user_permissions)
        optional_params = {
            'user_login': user_login,
            'user_permissions': user_permissions,
            'submenu_path': api.plugin_manager.get_submenu_path(ident),
        }
        res = {}
        # TODO: rozubudować w zależności od GUI_MODE i dostepnych funkcji
        # TODO2: sprawdzić i ew. rozbudować o kontrolę uprawnień!
        try:
            gui_mode = plugin.GUI_MODE
        except:
            if hasattr(plugin, 'LAUNCH_DIALOG'):
                gui_mode = 'report'
            else:
                gui_mode = 'unknown'
        dialog = api.plugin_manager.get_dialog_for_user(ident, 'LAUNCH', user_permissions)
        if dialog is not None:
            if 'on_show' in dialog.init_kwargs:
                dialog.init_kwargs['on_show']()
            res['dialog'] = dialog.get_definition()
        if hasattr(plugin, 'DOC') and plugin.DOC is not None:
            res['docs'] = plugin.DOC
        else:
            res['docs'] = None
        res['news'] = api.plugin_manager.get_news_for_user(ident, user_permissions)
        res['gui_mode'] = gui_mode
        if gui_mode == 'one_shot':
            res['content'] = call_with_optional_params(plugin.get_content, optional_params)
        if gui_mode == 'mailing':
            res['desc'] = getattr(plugin, 'DESC')
            res['table'] = getattr(plugin, 'MAILING_TABLE')
            res['dialog'] = getattr(plugin, 'MAILING_DIALOG').get_definition()
        if gui_mode == 'settings':
            res['desc'] = getattr(plugin, 'DESC')
            res['table'] = getattr(plugin, 'USERS_TABLE')
            res['dialog'] = getattr(plugin, 'USERS_DIALOG').get_definition()
        return res


@ns.route('/communicate/<string:ident>/<string:action>')
class PageCommunicate(APIResource):
    # TODO: sprawdzanie uprawnień do plugina

    def call_action(self, plugin, action, **kwargs):
        fn_name = 'action_%s' % action
        if not hasattr(plugin, fn_name):
            return None
        fn = getattr(plugin, fn_name)
        fn_kwargs = {}
        for k, v in kwargs.items():
            if k in inspect.getargs(fn.__code__).args:
                fn_kwargs[k] = v
        try:
            return fn(**fn_kwargs)
        except ValidationError as e:
            return {'status': 'error', 'error': str(e)}

    @login_required
    def get(self, ident, action, user_login, user_permissions):
        plugin = api.plugin_manager.find_plugin_by_path(ident)
        self.check_permissions(plugin, user_login, user_permissions)
        return self.call_action(plugin, action, user_login=user_login, user_permissions=user_permissions)

    @login_required
    def post(self, ident, action, user_login, user_permissions):
        plugin = api.plugin_manager.find_plugin_by_path(ident)
        data = request.json
        self.check_permissions(plugin, user_login, user_permissions)
        return self.call_action(plugin, action, user_login=user_login, user_permissions=user_permissions, data=data)


@ns.route('/dialog/<string:ident>/<string:typ>')
class DialogDefinition(APIResource):
    @login_required
    def get(self, ident, typ, user_login, user_permissions):
        plugin = api.plugin_manager.find_plugin_by_path(ident)
        self.check_permissions(plugin, user_login, user_permissions)
        dialog = api.plugin_manager.get_dialog_for_user(ident, typ, user_permissions)
        if dialog is not None:
            if 'on_show' in dialog.init_kwargs:
                dialog.init_kwargs['on_show']()
            return dialog.get_definition()
        else:
            return None


@ns.route('/dialog/<string:ident>/<string:typ>/<string:field>/data')
class WidgetData(APIResource):
    @login_required
    def post(self, ident, typ, field, user_login, user_permissions):
        plugin = api.plugin_manager.find_plugin_by_path(ident)
        self.check_permissions(plugin, user_login, user_permissions)
        params = request.json
        dialog = api.plugin_manager.get_dialog_for_user(ident, typ, user_permissions)
        if dialog is not None:
            field = dialog.get_field_by_name(field)
            if field is not None:
                return field.get_widget_data(params)
        return None


@ns.route('/action/<string:token>')
class ActionExecute(Resource):
    @login_required
    def get(self, token):
        action = TrustedAction.create_from_token(api.plugin_manager, token)
        if action is None:
            api.abort(404)
        return action.execute()
