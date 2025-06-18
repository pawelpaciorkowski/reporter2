from copy import copy
import inspect
import datetime
import jwt
import json
import base64
from Crypto import Random
from Crypto.Cipher import AES

from config import Config


# from dialog import ValidationError TODO XXX  - cykl zależności!!!!


class TrustedAction:
    params_available = None

    @classmethod
    def create_from_token(cls, plugin_manager, token):
        try:
            decoded = jwt.decode(token, key=Config.SECRET_KEY, verify=True)
        except jwt.exceptions.InvalidSignatureError:
            print('TA.cft error 1')
            return None
        token_exp = int(decoded['exp'])
        time_now = int(datetime.datetime.now().strftime('%s'))
        if time_now > token_exp:
            print('TA.cft error 2')
            return None
        plugin = plugin_manager.find_plugin_by_path(decoded['plg'])
        if plugin is None:
            print('TA.cft error 3')
            return None
        if not hasattr(plugin, decoded['cls']):
            print('TA.cft error 4')
            return None
        concr_cls = getattr(plugin, decoded['cls'])
        if not issubclass(concr_cls, cls):
            print('TA.cft error 5')
            return None
        return concr_cls(**decoded)

    def __init__(self, **kwargs):
        self.params = {}
        for param in self.params_available:
            if param in kwargs:
                self.params[param] = kwargs[param]

    def get_token(self):
        values = copy(self.params)
        values['exp'] = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime('%s')
        values['cls'] = self.__class__.__name__
        values['plg'] = inspect.getmodule(self.__class__).__PLUGIN__
        res = jwt.encode(values, key=Config.SECRET_KEY)
        if not isinstance(res, str):
            res = res.decode()
        return res

    def execute(self):
        raise NotImplementedError()


BLOCK_SIZE = 16


def _pad(s):
    return s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)


def _unpad(s):
    return s[:-ord(s[len(s) - 1:])]


def aes_encode(object, key):
    dumped = json.dumps(object)
    iv = Random.new().read(BLOCK_SIZE)
    aes = AES.new(key, AES.MODE_CFB, iv)
    return base64.b64encode(iv + aes.encrypt(_pad(dumped).encode())).decode()


def aes_decode(encoded, key):
    try:
        encoded = base64.b64decode(encoded)
        iv = encoded[:BLOCK_SIZE]
        aes = AES.new(key, AES.MODE_CFB, iv)
        decoded = _unpad(aes.decrypt(encoded[BLOCK_SIZE:]))
        return json.loads(decoded)
    except:
        return None


def wrap_trusted_value_for_user(value, user_id):
    packed = {'u': user_id, 'v': value}
    return aes_encode(packed, Config.SECRET_KEY)


def unwrap_trusted_value_from_user(encoded, user_id):
    packed = aes_decode(encoded, Config.SECRET_KEY)
    if packed is None:
        raise ValueError("Crypto error")
    if packed.get('u') != user_id:
        raise ValueError("Wrong user")
    return packed.get('v')
