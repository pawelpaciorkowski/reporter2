import hashlib
import tempfile
import os
import re
import base64
import json
import datetime


def decode_base64(data, altchars=b'+/'):
    data = re.sub(r'[^a-zA-Z0-9%s]+' % altchars, '', data)
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    return base64.b64decode(data, altchars)


def get_default_access_config_filename(refresh_token, base_dir=None):
    token_hash = hashlib.sha1(refresh_token.encode('utf-8')).hexdigest()[:8]
    if base_dir is None:
        base_dir = tempfile.gettempdir()
    return os.path.join(base_dir, 'api_access_%s.json' % token_hash)


def is_token_valid(token):
    segments = (token or '').split('.')
    if len(segments) < 2:
        raise ValueError("invalid token")
    token_data = json.loads(decode_base64(segments[1]).decode('utf-8'))
    now = int(datetime.datetime.now().strftime('%s'))
    return token_data['exp'] - now > 5


def get_best_url(url_list):
    return url_list[0]
    # TODO: wybieranie na podstawie ustawień sieciowych, np 2.0, zewnętrzny, 10....
