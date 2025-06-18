from .base import Field


class DynamicSelect(Field):
    def _prettify_params_value(self, params):
        res = Field._prettify_params_value(self, params)
        if isinstance(res, list):
            res = ', '.join(res)
        return res

    def load_own_value(self, value):
        available = [item['value'] for item in self.get_widget_data(None)]
        res = []
        if value is not None:
            if value == '*':
                for elem in available:
                    res.append(elem)
            else:
                for val in value.split(' '):
                    if len(val) > 0 and val in available:
                        res.append(val)
                    else:
                        print('NIE AVAIL', val, available)
        if self.init_kwargs.get('multiselect', False):
            return res
        elif len(res) > 0:
            return res[0]
        else:
            return None
