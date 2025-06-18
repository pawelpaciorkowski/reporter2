import json
import random
import string

import tornado
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.gen
from django.core.serializers.json import DjangoJSONEncoder
import jwt
from config import Config

cfg = Config()

# TODO: wiadomość autoryzująca z tokenem



@tornado.gen.coroutine
def sleep(interval):
    yield tornado.gen.sleep(interval)  # TODO: różne implementacje


class WebsocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        tornado.websocket.WebSocketHandler.__init__(self, application, request, **kwargs)
        self.user_token = None

    def check_origin(self, origin):
        return cfg.DEBUG

    def generate_token(self):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32))

    def write_message(self, type, token=None, **kwargs):
        if token is None:
            token = self.generate_token()
        msg = {
            'type': type,
            'token': token,
            'data': {}
        }
        for k, v in kwargs.items():
            msg['data'][k] = v
        tornado.websocket.WebSocketHandler.write_message(self, json.dumps(msg, sort_keys=True,
                                                                          indent=1,
                                                                          cls=DjangoJSONEncoder))

    @tornado.gen.coroutine
    def on_message(self, message):
        print('ON MESSAGE START', message)
        try:
            msg = json.loads(message)
            token = msg.get('token')
            if msg.get('type') == 'call':
                if msg.get('method') == 'authenticate':
                    try:
                        self.user_token = jwt.decode(msg['data']['token'], cfg.SECRET_KEY)
                        self.write_message('response', token, status='ok')
                    except:
                        self.write_message('response', token, status='error')
        except:
            pass


def make_app():
    return tornado.web.Application([
        (r"/ws", WebsocketHandler),
    ])


if __name__ == "__main__":
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(5001)
    tornado.ioloop.IOLoop.instance().start()
