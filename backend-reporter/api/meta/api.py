from api.restplus import api
ns = api.namespace('meta', description="Endpointy dla specyficznych widoków")
from . import my_reports
