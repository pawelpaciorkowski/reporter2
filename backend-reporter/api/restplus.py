import logging
import traceback
import datetime
import json

from flask_restx import Api, fields, reqparse
from sqlalchemy.orm.exc import NoResultFound
try:
    from flask.json import JSONEncoder
except ImportError:
    from json import JSONEncoder


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, datetime.date) or isinstance(obj, datetime.datetime):
                return obj.isoformat()
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


def json_encode(obj):
    return json.dumps(obj)


api = Api(title='Alab Reporter API')

pagination_arguments = reqparse.RequestParser()
pagination_arguments.add_argument('page', type=int, required=False, default=1, help='Page number')
pagination_arguments.add_argument('per_page', type=int, required=False, choices=[2, 10, 20, 30, 40, 50],
                                  default=10, help='Results per page {error_msg}')

pagination = api.model('A page of results', {
    'page': fields.Integer(description='Number of this page of results'),
    'pages': fields.Integer(description='Total number of pages of results'),
    'per_page': fields.Integer(description='Number of items per page of results'),
    'total': fields.Integer(description='Total number of results'),
    'debug': fields.String(description='Additional debug info'),
})

status = api.model('Status', {
    'ok': fields.Boolean(required=True, description='Status wykonania'),
    'msg': fields.String(required=False, description="Dodatkowy komunikat"),
})

log = logging.getLogger(__name__)


@api.errorhandler
def default_error_handler(e):
    message = 'Wystąpił błąd'
    log.exception(message)
    # jeśli nie debug to return {'message': message}, 500


@api.errorhandler(NoResultFound)
def database_not_found_error_handler(e):
    log.warning(traceback.format_exc())
    return {'message': 'Nie znaleziono.'}, 404
