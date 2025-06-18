import datetime
import base64
from outlib.xlsx import ReportXlsx
from outlib.pdf import ReportPdf
from outlib.csv import ReportCsv
from helpers import slugify


DEFAULT_LABELS = {
    'xlsx': 'Excel',
    'pdf': 'PDF',
    'csv': 'CSV'
}

DEFAULT_ICONS = {
    'xlsx': 'panel-table',
    'pdf': 'print',
    'csv': 'panel-table'
}


class ReportActionExecutor:
    def __init__(self, action):
        self.action = action

    def get_filename(self, plugin, result, extension, timestamp=None, fn_prefix=None):
        fn = 'eksport'
        if hasattr(plugin, 'MENU_ENTRY'):
            fn = slugify(plugin.MENU_ENTRY)
        if timestamp is not None:
            fn += timestamp.strftime('_%Y%m%d_%H%M%S')
        else:
            fn += datetime.datetime.now().strftime('_%Y%m%d_%H%M%S')
        fn += '.' + extension
        if fn_prefix is not None:
            fn = fn_prefix + '_' + fn
        return fn

    def execute(self, plugin, result, timestamp=None, fn_prefix=None):
        if 'title' not in self.action:
            if hasattr(plugin, 'LAUNCH_DIALOG'):
                try:
                    self.action['title'] = plugin.LAUNCH_DIALOG.init_kwargs['title']
                except:
                    pass
            if 'title' not in self.action and hasattr(plugin, 'MENU_ENTRY'):
                self.action['title'] = plugin.MENU_ENTRY
        if self.action['type'] == 'xlsx':
            xlsx = ReportXlsx(result, **self.action)
            content = base64.b64encode(xlsx.render_as_bytes()).decode()
            return {
                'type': 'download',
                'filename': self.get_filename(plugin, result, 'xlsx', timestamp=timestamp, fn_prefix=fn_prefix),
                'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'content': content
            }
        elif self.action['type'] == 'pdf':
            pdf = ReportPdf(result, **self.action)
            content = base64.b64encode(pdf.render_as_bytes()).decode()
            return {
                'type': 'download',
                'filename': self.get_filename(plugin, result, 'pdf', timestamp=timestamp, fn_prefix=fn_prefix),
                'content_type': 'application/pdf',
                'content': content
            }
        elif self.action['type'] == 'csv':
            csv = ReportCsv(result, **self.action)
            content = base64.b64encode(csv.render_as_bytes()).decode()
            return {
                'type': 'download',
                'filename': self.get_filename(plugin, result, 'csv', timestamp=timestamp, fn_prefix=fn_prefix),
                'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'content': content
            }
        else:
            raise Exception('Unknown action type', self.action.get('type'))


class ReportActions:
    def __init__(self, actions):
        self.actions = actions
        self.augmented_actions = None

    def get_augmented_actions(self):
        if self.augmented_actions is None:
            self.augmented_actions = []
            for idx, act in enumerate(self.actions):
                if isinstance(act, str):
                    act = {'type': act}
                act['_index'] = idx
                if 'label' not in act:
                    act['label'] = DEFAULT_LABELS.get(act['type'], '[UNKNOWN]')
                if 'icon' not in act and act['type'] in DEFAULT_ICONS:
                    act['icon'] = DEFAULT_ICONS[act['type']]
                self.augmented_actions.append(act)
        return self.augmented_actions

    def get_action_executor(self, action_type, action_index):
        actions = self.get_augmented_actions()
        if action_index < 0 or action_index >= len(actions):
            return None
        if action_type != actions[action_index]['type']:
            return None
        return ReportActionExecutor(actions[action_index])
