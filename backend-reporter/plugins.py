import datetime
import os, sys, fnmatch
import time
from copy import copy
import markdown
try:
    import imp
except ImportError:
    imp = None
    import importlib.util
    # print("Brak modułu imp - za nowy Python, PluginManager nie będzie działać", file=sys.stderr)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'api-access-python-client')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'api-access-python-server')))
try:
    from api_access_client import ApiAccessManager
    from api_access_server.common import ApiAccessTokenData
except ImportError:
    print("\n\033[1mBrak submodułów - uruchom git submodule init; git submodule update\033[0m\n")
    raise

ROLE_CONTAINMENT = {
    'ADMIN': ['C-ADM', 'HIST', 'C-IT'],
    'C-ADM': ['C-ALL', 'R-ADM', 'L-ADM'],
    'C-ALL': ['C-CS', 'C-FIN', 'C-ROZL', 'R-DYR', 'R-PM', 'HIST'],
    'R-ADM': ['L-ADM', 'R-CS', 'R-PP'],
    'C-CS': ['C-CS-OF', 'R-CS', 'C-PP'],
    'C-PP': ['R-PP'],
    'R-PP': ['L-PP'],
    'R-CS': ['L-KIER', 'R-PP'],
    'R-MDO': ['L-KIER'],
    'L-KIER': ['L-PRAC', 'L-PP'],
    'HIST': ['H-ROZL', 'H-QA', 'H-PRAC'],
    'R-DYR': ['C-DS'],
}


def extend_role_filter(filter):
    if filter is None:
        return None
    res = copy(filter)
    zmiana = True
    while zmiana:
        zmiana = False
        for nadrola, podrole in ROLE_CONTAINMENT.items():
            for podrola in podrole:
                if podrola in res and nadrola not in res:
                    res.append(nadrola)
                    zmiana = True
    return res


def merge_role_filter(upper, current):
    if current is None:
        return upper
    if isinstance(current, str):
        current = [current]
    if upper is None:
        return extend_role_filter(current)
    res = []
    for role in extend_role_filter(current):
        if role in upper:
            res.append(role)
    return res

def load_module(dirname, modname):
    if imp:
        f, p, d = imp.find_module(modname, [dirname])
        return imp.load_module(modname, f, p, d)
    else:
        modpath = str(os.path.join(dirname, modname))
        if os.path.isfile(modpath + '.py'):
            spec = importlib.util.spec_from_file_location(modname, modpath + '.py')
        elif os.path.isdir(modpath):
            spec = importlib.util.spec_from_file_location(modname, os.path.join(modpath, '__init__.py'))
        else:
            raise RuntimeError(modpath, "not found")
        module = importlib.util.module_from_spec(spec)
        sys.modules[modname] = module
        if spec.loader is not None:
            if hasattr(module, '__path__'):
                module.__package__ = modname
            else:
                module.__package__ = modname.rsplit('.', 1)[0]
            spec.loader.exec_module(module)
        return module

class LazyModule:
    def __init__(self, mod_name, search_path):
        self.mod_name = mod_name
        self.search_path = search_path
        self.real_module = None
        self._init_keys = [k for k in self.__dict__.keys()] + ['_init_keys']

    def get_real_module(self):
        if self.real_module is not None:
            return self.real_module
        # f, p, d = imp.find_module(self.mod_name, [self.search_path])
        # module = imp.load_module(self.mod_name, f, p, d)
        module = load_module(self.search_path, self.mod_name)
        if hasattr(module, 'init_plugin'):
            module.init_plugin()
        for k in self.__dict__.keys():
            if k not in self._init_keys:
                module.__dict__[k] = self.__dict__[k]
        self.real_module = module
        return module

_PLUGIN_MANAGER = None

class PluginManager:
    def __init__(self, lazy=False):
        self.lazy = lazy
        self.menu = []
        self.role_extensions = {}
        self.templaters = self.collect_templates_dir('templates')
        self.plugin_packs = {
            'raporty': self.collect_plugins_dir('raporty'),
            'extras': self.collect_plugins_dir('extras'),
            'meta': self.collect_plugins_dir('meta'),
        }
        # TODO: uzupełnić GUI_MODE na report dla self.plugin_packs['raporty']
        self.plugins = []
        for k, v in self.plugin_packs.items():
            self.plugins.append(v)
        menu_parts = [
            self.plugin_packs['raporty'],
            self.plugin_packs['extras'],
            self.plugin_packs['meta'],
        ]
        # TODO XXX: do menu zbierać tylko to co ma MENU_ENTRY, przy okazji zapisywać uprawnienia i to czy coś jest
        #  generowane dla usera na ążdanie
        for part in menu_parts:
            # TODO: można by to wyrzucić do rekurencyjnej procedurki
            if part.get('menu_entry') is not None:
                self.menu.append(part)
            else:
                for subpart in part.get('children', []):
                    self.menu.append(subpart)

    @classmethod
    def singleton(cls):
        global _PLUGIN_MANAGER
        if _PLUGIN_MANAGER is None:
            _PLUGIN_MANAGER = PluginManager()
        return _PLUGIN_MANAGER

    def load_module(self, mod_name, search_path=None):
        if search_path is None:
            search_path = os.getcwd()
        if self.lazy:
            return LazyModule(mod_name, search_path)
        else:
            # f, p, d = imp.find_module(mod_name, [search_path])
            # module = imp.load_module(mod_name, f, p, d)
            module = load_module(search_path, mod_name)
            if hasattr(module, 'init_plugin'):
                module.init_plugin()
            return module

    def load_module_from_file(self, filename):
        search_path = os.path.dirname(filename)
        mod_name = os.path.basename(filename).replace('.py', '')
        # f, p, d = imp.find_module(mod_name, [search_path])
        # return imp.load_module(mod_name, f, p, d)
        return load_module(search_path, mod_name)

    def get_module(self, module):
        if isinstance(module, LazyModule):
            res = module.get_real_module()
            self.template_module_if_needed(res)
            return res
        return module

    # TODO: na każdym poziomie sprawdzać uprawnienia
    def find_plugin_and_submenu_by_path(self, path, credentials=None, startingWith=None, level=0):
        if isinstance(path, str):
            path = path.split('.')
            return self.find_plugin_and_submenu_by_path(path, credentials, startingWith, level)
        if startingWith is None:
            startingWith = self.plugins
        # print('FPBP', level, startingWith)
        if len(path) == level:
            return self.get_module(startingWith['module']), None
        if isinstance(startingWith, list):
            for elem in startingWith:
                path_cmp = path[level]
                elem_path = elem['path'].split('/')
                elem_path_cmp = elem_path[level]
                if ':' in path_cmp:
                    path_cmp = path_cmp.split(':')[1]
                if ':' in elem_path_cmp:
                    elem_path_cmp = elem_path_cmp.split(':')[1]
                # print('LIST', path, elem_path, level, path[level])
                if elem_path_cmp == path_cmp:
                    return self.find_plugin_and_submenu_by_path(path, credentials, elem, level + 1)
        elif isinstance(startingWith, dict):
            # print('DICT', startingWith)
            if 'children' in startingWith:
                return self.find_plugin_and_submenu_by_path(path, credentials, startingWith['children'], level)
            else:
                plugin = self.get_module(startingWith['module'])
                submenu = '.'.join(path[level:])
                # print('WITH SUBMENU', plugin, submenu)
                return plugin, submenu
        else:
            raise TypeError('Struktura szukania pluginów', startingWith)

    def find_plugin_by_path(self, path, credentials=None):
        res = self.find_plugin_and_submenu_by_path(path, credentials=credentials)
        if res is None:
            return None
        plugin, _ = res
        return plugin

    def get_submenu_path(self, path, credentials=None):
        plugin, submenu = self.find_plugin_and_submenu_by_path(path, credentials=credentials)
        return submenu

    def check_role_for_menu(self, role, menu):
        if self.lazy:
            raise NotImplemented('Menu niedostępne przy leniwym ładowaniu modułów')
        can_access = False
        if '.' in role:
            if role.startswith(menu['path'].replace('/', '.')):
                can_access = True
        elif menu['module'].__ROLE_FILTER__ is not None:
            if role in menu['module'].__ROLE_FILTER__ or '*' in menu['module'].__ROLE_FILTER__:
                can_access = True
        if not can_access and role in self.role_extensions:
            for subrole in self.role_extensions[role]:
                can_access = can_access or self.check_role_for_menu(subrole, menu)
        return can_access

    def get_menu_for_user(self, user_permissions):
        # TODO XXX - filtrowanie po uprawnieniach, a najlepiej jechać po pluginach tak jak w find_plugin_by_path
        if self.lazy:
            raise NotImplemented('Menu niedostępne przy leniwym ładowaniu modułów')

        def build_menu(menu):
            if isinstance(menu, list):
                res = []
                for elem in menu:
                    reselem = build_menu(elem)
                    if reselem is not None:
                        res.append(reselem)
                return res
            elif isinstance(menu, dict) and 'module' in menu:
                can_access = False
                if menu['module'].__ROLE_FILTER__ is not None and '*' in menu['module'].__ROLE_FILTER__:
                    can_access = True
                else:
                    for role, labs in user_permissions:
                        can_access = can_access or self.check_role_for_menu(role, menu)
                if can_access:
                    res = {}
                    for k, v in menu.items():
                        if k == 'children':
                            v = build_menu(v)
                        res[k] = v
                    if 'module' in menu and hasattr(menu['module'], 'submenu_for_user'):
                        res['lazyLoad'] = True
                        res['lazyChildren'] = 'submenu:%s' % res['dotpath']
                    return res
                else:
                    return None
            else:
                raise Exception('Nieprawidłowy typ w menu', menu)

        return build_menu(self.menu)

    def get_submenu_for_user(self, path):
        plugin = self.find_plugin_by_path(path)
        menu_path = '/' + path.replace('.', '/')
        if hasattr(plugin, 'submenu_for_user'):
            submenu = plugin.submenu_for_user()
            if submenu is not None and len(submenu) > 0:
                res = []
                for i, (subpath, title) in enumerate(submenu):
                    full_path = (menu_path + '/' + subpath).replace('//', '/')
                    res.append({
                        'id': i,
                        'label': title,
                        'url': full_path,
                    })
                return res
        return None

    def get_dialog_for_user(self, ident, typ, credentials):
        plugin = self.find_plugin_by_path(ident, credentials)
        if plugin is None:
            return None
        dialog_name = typ + '_DIALOG'
        if dialog_name in plugin.__dict__:
            dialog = plugin.__dict__[dialog_name]
            if 'HELP' in plugin.__dict__:
                dialog.set_help(plugin.HELP)
            return dialog
        return None

    def load_news_from_plugin(self, res, plugin, data_old, credentials):
        if hasattr(plugin, 'NEWS'):
            for data, content in plugin.NEWS:
                target = 'current' if data >= data_old else 'old'
                res[target].append({
                    'data': data,
                    'content': self.load_markdown(content),
                    'report': plugin.__PLUGIN__.replace('.', '/'),
                    'reportTitle': getattr(plugin, 'MENU_ENTRY')
                })

    def get_all_plugins_for_user_in(self, ident, credentials):
        res = []

        def walk_flat(menu):
            res = []
            for item in menu:
                res.append(item['module'])
                if 'children' in item:
                    res += walk_flat(item['children'])
            return res

        menu = self.get_menu_for_user(credentials)
        for module in walk_flat(menu):
            if module.__PLUGIN__.startswith(ident):
                res.append(module)
        return res

    def get_news_for_user(self, ident, credentials):
        res = {'current': [], 'old': []}
        data_old = (datetime.datetime.now() - datetime.timedelta(days=31)).strftime('%Y-%m-%d')
        for plugin in self.get_all_plugins_for_user_in(ident, credentials):
            self.load_news_from_plugin(res, plugin, data_old, credentials)
        if len(res['current']) + len(res['old']) == 0:
            return None
        for fld in ('current', 'old'):
            res[fld] = sorted(res[fld], key=lambda n: n['data'], reverse=True)
        return res

    def get_search_texts(self, module):
        texts_l1 = []
        texts_l2 = []

        if not hasattr(module, 'LAUNCH_DIALOG') and not hasattr(module, 'get_result'):
            return ([], [])

        def walk_widget(widget):
            res = []
            if widget.__class__.__name__ == 'InfoText':
                if 'text' in widget.init_kwargs:
                    res.append(widget.init_kwargs['text'])
            if 'children' in widget.init_kwargs:
                for child in widget.init_kwargs['children']:
                    res += walk_widget(child)
            if hasattr(widget, 'children'):
                for child in widget.children:
                    res += walk_widget(child)
            return res

        if hasattr(module, 'MENU_ENTRY'):
            texts_l1.append(module.MENU_ENTRY)
        if hasattr(module, 'LAUNCH_DIALOG'):
            dialog = module.LAUNCH_DIALOG
            if 'title' in dialog.init_kwargs:
                texts_l1.append(dialog.init_kwargs['title'])
            if 'help' in dialog.init_kwargs:
                texts_l2.append(dialog.init_kwargs['help'])
            for text in walk_widget(dialog):
                texts_l2.append(text)

        texts_l1.append(module.__name__.split('/')[-1])
        return (
            [text for text in texts_l1 if text is not None and text != ''],
            [text for text in texts_l2 if text is not None and text != '']
        )

    def template_module(self, module, template):
        if template not in self.templaters:
            raise RuntimeError("Template %s not found for module %s" % (template, str(module)))
        templater_class = self.templaters[template]
        templater = templater_class(module)
        templater.template()

    def template_module_if_needed(self, module):
        if isinstance(module, LazyModule):
            return
        if not hasattr(module, 'TEMPLATE'):
            return
        self.template_module(module, module.TEMPLATE)

    def collect_templates_dir(self, katalog):
        res = {}
        for fn in sorted(os.listdir(katalog)):
            full_fn = katalog + '/' + fn
            if os.path.isfile(full_fn) and full_fn.endswith('.py') and not full_fn.endswith('__init__.py'):
                templater_name = os.path.basename(full_fn).split('.')[0]
                templater_mod = self.load_module_from_file(full_fn)
                res[templater_name] = templater_mod.Template
        return res

    def collect_plugins_dir(self, katalog, role_filter=None):
        res = {}
        if os.path.exists(katalog + '/__init__.py') and not os.path.exists(katalog + '/NOT_A_PLUGIN'):
            res['path'] = katalog
            res['module'] = self.load_module(katalog.split('/')[-1], os.path.dirname(katalog))
            self.template_module_if_needed(res['module'])
            if 'MENU_ENTRY' in res['module'].__dict__:
                res['menu_entry'] = res['module'].MENU_ENTRY
            if 'GUI_MODE' in res['module'].__dict__:
                res['gui_mode'] = res['module'].GUI_MODE
            res['module'].__dict__['__ROLE_FILTER__'] = merge_role_filter(role_filter,
                                                                          res['module'].__dict__.get('REQUIRE_ROLE'))
            res['module'].__dict__['__PLUGIN__'] = katalog.replace('/', '.')
            docfile = os.path.join(katalog, 'doc.md')
            if not self.lazy and os.path.exists(docfile):
                res['module'].__dict__['DOC'] = self.load_doc(docfile)
            else:
                res['module'].__dict__['DOC'] = None
            res['children'] = []
            for fn in sorted(os.listdir(katalog)):
                full_fn = katalog + '/' + fn
                if os.path.isdir(full_fn):
                    potential_module = self.collect_plugins_dir(full_fn, role_filter=res['module'].__ROLE_FILTER__)
                    if potential_module is not None:
                        res['children'].append(potential_module)
                elif os.path.isfile(full_fn) and full_fn.endswith('.py') and not full_fn.endswith('__init__.py'):
                    child = {
                        'module': self.load_module(fn.replace('.py', ''), katalog),
                        'path': full_fn.replace('.py', '')
                    }
                    child['dotpath'] = child['path'].replace('/', '.')
                    self.template_module_if_needed(child['module'])
                    if hasattr(child['module'], 'GUI_MODE'):
                        path = child['path'].split('/')
                        path[-1] = '%s:%s' % (child['module'].GUI_MODE, path[-1])
                        child['path'] = '/'.join(path)
                    child['module'].__dict__['__PLUGIN__'] = child['dotpath']
                    child['module'].__dict__['__ROLE_FILTER__'] = merge_role_filter(res['module'].__ROLE_FILTER__,
                                                                                    child['module'].__dict__.get(
                                                                                        'REQUIRE_ROLE'))
                    if hasattr(child['module'], 'ADD_TO_ROLE'):
                        roles = child['module'].__dict__['ADD_TO_ROLE']
                        if not isinstance(roles, list):
                            roles = [roles]
                        for role in roles:
                            if role not in self.role_extensions:
                                self.role_extensions[role] = []
                            self.role_extensions[role].append(child['dotpath'])
                    if 'MENU_ENTRY' in child['module'].__dict__:
                        child['menu_entry'] = child['module'].MENU_ENTRY
                        if 'GUI_MODE' in child['module'].__dict__:
                            child['gui_mode'] = child['module'].GUI_MODE
                        res['children'].append(child)
                    elif self.lazy:
                        res['children'].append(child)
                    docfile = full_fn[:-2] + 'md'
                    if not self.lazy and os.path.exists(docfile):
                        child['module'].__dict__['DOC'] = self.load_doc(docfile)
                    else:
                        child['module'].__dict__['DOC'] = None
        else:
            return None
        return res

    def can_access(self, rola, sciezka):
        plugin = self.find_plugin_by_path(sciezka)
        if plugin is None:
            return False
        if plugin.__ROLE_FILTER__ is None:
            return True
        if '*' in plugin.__ROLE_FILTER__ and rola is not None:
            return True
        if rola in plugin.__ROLE_FILTER__:
            return True
        if rola == sciezka:
            return True
        if rola in self.role_extensions:
            for subrola in self.role_extensions[rola]:
                if self.can_access(subrola, sciezka):
                    return True
        return False

    def is_executable(self, module):
        if hasattr(module, 'LAUNCH_DIALOG'):
            return True
        return False

    def load_markdown(self, content):
        lines = content.split('\n')
        start = 999
        for line in lines:
            stripped = len(line.lstrip(' '))
            if stripped == 0:
                continue
            pref_spaces = len(line) - stripped
            if pref_spaces < start:
                start = pref_spaces
        content = '\n'.join([line[start:] for line in lines])
        res = markdown.markdown(content, extensions=['markdown.extensions.tables', 'markdown.extensions.wikilinks'])
        # TODO: linki
        return res

    def load_doc(self, fn):
        with open(fn, 'r') as f:
            content = f.read()
        return self.load_markdown(content)