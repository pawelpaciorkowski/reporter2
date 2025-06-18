from .base import Widget, Field
from helpers import format_rst


class Container(Widget):
    pass


class PrimitiveContainer(Container):
    def get_definition(self):
        res = {'children': []}
        for sub in self.init_args:
            if sub is not None:
                res['children'].append(sub.get_definition())
        for k, v in self.init_kwargs.items():
            res[k] = v
        return self.pack_definition_result(res)

    @property
    def children(self):
        return self.init_args


class Panel(Container):
    def __init__(self, panel, *args, **kwargs):
        kwargs['children'] = [panel]
        Container.__init__(self, *args, **kwargs)


class Dialog(Panel):
    def set_help(self, help):
        self.init_kwargs['help'] = help

    def get_definition_only(self):
        res = Panel.get_definition_only(self)
        if 'help' in self.init_kwargs:
            res['help'] = format_rst(self.init_kwargs['help'])
        return res


class HBox(PrimitiveContainer):
    pass


class VBox(PrimitiveContainer):
    pass


class TabbedView(Container, Field):
    def prettify_params(self, params, result=None):
        caption = self._prettify_params_caption()
        value = self._prettify_params_value(params)
        for cld in self.children:
            if cld.init_kwargs.get('value') == value:
                result.append([caption, cld.init_kwargs.get('title', value)])
                cld.prettify_params(params, result)
        return result


class Tab(Panel):
    pass


class InfoText(Widget):
    pass
