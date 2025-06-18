import re
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch, Preset
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, slugify


class Template:
    default_settings = {
        'multiple_labs': False,
        'dialog_title': None,
    }

    def __init__(self, module):
        self.module = module
        self.settings = {}
        for k, v in getattr(module, 'SETTINGS', {}).items():
            self.settings[k] = v
        for k, v in self.default_settings.items():
            if k not in self.settings:
                self.settings[k] = v
        self.scan_sql()

    def scan_sql(self):
        self.sql = getattr(self.module, 'SQL')
        self.fields = []
        self.form_fields = {}
        self.param_args = []
        for field in re.findall(r':"[^"]+"', self.sql):
            field = field[2:-1]
            if '$' not in field:
                field = 'T$' + field
            if field not in self.fields:
                self.fields.append(field)
                [type, title] = field.split('$', 1)
                self.form_fields[field] = {
                    'type': type,
                    'title': title,
                    'slug': slugify(title)
                }
            self.param_args.append(self.fields.index(field))
        self.target_sql = re.sub(r':"[^"]+"', '?', self.sql)
        if hasattr(self.module, 'SQL_PG'):
            self.target_sql_pg = re.sub(r':"[^"]+"', '?', getattr(self.module, 'SQL_PG'))
        else:
            self.target_sql_pg = self.target_sql

    def generate_launch_dialog(self):
        title = self.settings['dialog_title'] or getattr(self.module, 'MENU_ENTRY')
        controls = []
        if hasattr(self.module, 'HELP'):
            controls.append(InfoText(text=getattr(self.module, 'HELP')))
        if self.settings['multiple_labs']:
            controls.append(LabSelector(field="labs", title="Laboratoria", multiselect=True))
        else:
            controls.append(LabSelector(field="lab", title="Laboratorium", multiselect=False))
        for field in self.fields:
            field_def = self.form_fields[field]
            if field_def['type'] == 'D':
                field_class = DateInput
            else:
                field_class = TextInput
            controls.append(field_class(field=field_def['slug'], title=field_def['title']))
        self.module.LAUNCH_DIALOG = Dialog(title=title, panel=VBox(*controls))

    def generate_start_report(self):
        def start_report(params):
            params = self.module.LAUNCH_DIALOG.load_params(params)
            for field in self.fields:
                field_def = self.form_fields[field]
                if empty(params[field_def['slug']]):
                    raise ValidationError("Nie wypełniono %s" % field_def['title'])
            if self.settings['multiple_labs']:
                labs = params['labs']
            else:
                labs = [params['lab']]
            if len(labs) == 0:
                raise ValidationError("Wybierz laboratorium")
            report = TaskGroup(self.module.__PLUGIN__, params)
            for lab in labs:
                task = {
                    'type': 'centrum',
                    'priority': 1,
                    'target': lab,
                    'params': params,
                    'function': 'report_lab'
                }
                report.create_task(task)
            report.save()
            return report

        self.module.start_report = start_report

    def generate_report_function(self):
        def report_lab(task_params):
            params = task_params['params']
            with get_centrum_connection(task_params['target']) as conn:
                sql = self.target_sql_pg if conn.db_engine == 'postgres' else self.target_sql
                sql_params = [params[self.form_fields[self.fields[idx]]['slug']] for idx in self.param_args]
                cols, rows = conn.raport_z_kolumnami(sql, sql_params)
                return {
                    'type': 'table',
                    'header': cols,
                    'data': prepare_for_json(rows),
                }

        self.module.report_lab = report_lab

    def generate_get_results(self):
        pass

    def template(self):
        self.generate_launch_dialog()
        self.generate_start_report()
        self.generate_report_function()
        self.generate_get_results()
