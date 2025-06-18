import pytest
import mock

import jwt

from config import Config


class MockedRequest:
    def __init__(self, config):
        self.config = config

    def __enter__(self):
        self.request = mock.patch('api.auth.utils.request').__enter__()
        if self.config.authenticated:
            token = jwt.encode(
                {'iss': 'reporter', 'sub': 'test', 'user': self.config.user_id, 'rights': self.config.rights},
                Config.SECRET_KEY, algorithm='HS512')
            self.request.headers.get.return_value = 'bearer %s' % token.decode()
        else:
            self.request.headers.value = {}
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.request.__exit__(exc_type, exc_val, exc_tb)


class with_mocked_request:
    def __init__(self, authenticated=True, rights=None, user_id=0):
        self.authenticated = authenticated
        self.rights = rights
        self.user_id = user_id
        if authenticated and self.rights is None:
            self.rights = 'L-KIER:CZERNIA KOPERNI SIEDLCE PEKIN'

    def __call__(self, test_function):
        def wrapper(*args, **kwargs):
            with MockedRequest(self):
                return test_function(*args, **kwargs)

        return wrapper
