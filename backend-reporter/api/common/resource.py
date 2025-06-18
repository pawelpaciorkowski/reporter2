from api.restplus import api
from flask_restx import Resource


class APIResource(Resource):
    def check_permissions(self, plugin, user_login, user_permissions):
        # # TODO: nie ma sprawdzania zasięgu
        if plugin is None:
            api.abort(404, 'Nie znaleziono')
        for perm_name, perm_range in user_permissions:
            if api.plugin_manager.can_access(perm_name, plugin.__PLUGIN__):
                return True
        api.abort(401, 'Brak dostępu')
