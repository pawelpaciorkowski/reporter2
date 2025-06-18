from helpers import wrap_trusted_value_for_user, unwrap_trusted_value_from_user
from api.auth import login_required
from .base import Field


class DynamicSearch(Field):
    @login_required
    def load_own_value(self, value, user_id):
        res = []
        if value is not None:
            for val in value.split(' '):
                if len(val) > 0:
                    res.append(unwrap_trusted_value_from_user(val, user_id))
        if self.init_kwargs.get('multiselect', False):
            return res
        elif len(res) > 0:
            return res[0]
        else:
            return None

    @login_required
    def get_widget_data(self, params, user_id):
        res = Field.get_widget_data(self, params)
        for row in res:
            if 'value' in row:
                row['value'] = wrap_trusted_value_for_user(row['value'], user_id)
        return res