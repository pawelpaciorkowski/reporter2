import json

from flask import Flask, Blueprint, render_template, send_from_directory
import os
import logging.config
from plugins import PluginManager
import config
cfg = config.Config()

if cfg.SENTRY_URL is not None:
    import sentry_sdk
    sentry_sdk.init(cfg.SENTRY_URL)

app = Flask(__name__, static_folder='static/static', template_folder='static', static_url_path='/static/')
app.config.from_object('config.Config')

logging_conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'logging.conf'))
logging.config.fileConfig(logging_conf_path)
log = logging.getLogger(__name__)

from api.restplus import api

from api.auth import ns as ns_auth, user_cli, cfg_cli
from api.gui import ns as ns_gui
from api.report import ns as ns_report
from api.external import ns as ns_external
from api.meta import ns as ns_meta

@app.route('/', methods=['GET'], defaults={'path': ''})
@app.route('/<path:path>')
def home(path):
    # return render_template('/index.html', title="Index")
    api.abort(404)


# TODO: przenieść gdzieś indziej

api.plugin_manager = PluginManager()

from datetime import datetime
from werkzeug.routing import BaseConverter, ValidationError


class DateConverter(BaseConverter):
    """Extracts a ISO8601 date from the path and validates it."""

    regex = r'\d{4}-\d{2}-\d{2}'

    def to_python(self, value):
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError()

    def to_url(self, value):
        return value.strftime('%Y-%m-%d')


app.url_map.converters['date'] = DateConverter

"""
TODO XXX - poniższe mogłoby działać z samymy Flask, ale nie z Flask Restplus

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return list(o)
        if isinstance(o, datetime):
            return str(o)
        return json.JSONEncoder.default(self, o)

app.json_encoder = JSONEncoder

-- trzeba używać modeli, jeśli chcemy przesyłać bardziej skomplikowane wartości
"""

# TODO: dotąd


# TODO: zależnie od ustawienia debug / devel
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'content-type, authorization')
    return response


api_blueprint = Blueprint('api', __name__, url_prefix='/api')
api.init_app(api_blueprint)
api.add_namespace(ns_auth)
api.add_namespace(ns_gui)
api.add_namespace(ns_report)
api.add_namespace(ns_external)
api.add_namespace(ns_meta)
app.register_blueprint(api_blueprint)
app.cli.add_command(user_cli)
app.cli.add_command(cfg_cli)

if __name__ == '__main__':
    # TODO: w mainie można też inne rzeczy poustawiać pod debug, np CORS
    app.run(debug=True, host="127.0.0.1", port=5000, reloader_type='stat')

application = app

