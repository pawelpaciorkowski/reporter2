import inspect

try:
    from helpers.widget_data import WidgetDataProvider
except ImportError:
    WidgetDataProvider = None


class ValidationError(Exception):
    pass


class Widget(object):
    datasource = None

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs

    def pack_definition_result(self, res):
        hierarchy = [cls.__name__ for cls in inspect.getmro(self.__class__)][:-2]
        return [self.__class__.__name__, hierarchy, res]  # TODO: zastanowić się nad nadklasami

    def get_definition(self):
        res = self.get_definition_only()
        return self.pack_definition_result(res)

    def get_definition_only(self):
        res = {}
        # TODO: args nie obsługujemy
        for k, v in self.init_kwargs.items():
            if k == 'children':
                res['children'] = []
                for sub in v:
                    if sub is not None:
                        res['children'].append(sub.get_definition())
            else:
                if not callable(v):  # TODO: jeśli jakieś inne atrybuty mają być wyłączane, to tu dodać sprawdzenie
                    res[k] = v
        return res

    @property
    def children(self):
        return self.init_kwargs.get('children', [])

    def get_widget_data(self, params):
        if WidgetDataProvider is not None:
            wdp = WidgetDataProvider(self)
            return wdp.get_widget_data(self, params)
        else:
            return None

    def load_own_value(self, value):
        return value

    def get_default_value(self):
        if 'default' in self.init_kwargs:
            return self.init_kwargs['default']
        return None

    def load_params(self, params):
        res = {}
        if 'field' in self.init_kwargs:
            res[self.init_kwargs['field']] = self.load_own_value(params.get(self.init_kwargs['field']))
        for cld in self.children:
            for k, v in cld.load_params(params).items():
                res[k] = v
        return res

    def prettify_params(self, params, result=None):
        if result is None:
            result = []
        for cld in self.children:
            cld.prettify_params(params, result)
        return result

    def get_field_by_name(self, name):
        if 'field' in self.init_kwargs and self.init_kwargs['field'] == name:
            return self
        for cld in self.children:
            res = cld.get_field_by_name(name)
            if res is not None:
                return res
        return None


class Field(Widget):
    def get_definition_only(self):
        res = Widget.get_definition_only(self)
        dv = self.get_default_value()
        if dv is not None:
            res['default_value'] = dv
        return res

    def _prettify_params_caption(self):
        if 'desc_title' in self.init_kwargs:
            return self.init_kwargs['desc_title']
        elif 'title' in self.init_kwargs:
            return self.init_kwargs['title']
        elif 'field' in self.init_kwargs:
            return self.init_kwargs['field']
        else:
            return ''

    def _prettify_params_value(self, params):
        if 'field' in self.init_kwargs:
            if self.init_kwargs['field'] in params:
                return params[self.init_kwargs['field']]
            else:
                return '---'
        else:
            return None

    def prettify_params(self, params, result=None):
        caption = self._prettify_params_caption()
        value = self._prettify_params_value(params)
        if value is not None and value != '':
            result.append([caption, value])
        return Widget.prettify_params(self, params, result)
