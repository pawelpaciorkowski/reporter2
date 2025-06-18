import pytest
from werkzeug.exceptions import Forbidden

from dialog import ValidationError
from helpers import wrap_trusted_value_for_user, unwrap_trusted_value_from_user
from test_utils import with_mocked_request
from config import Config


@with_mocked_request(authenticated=False)
def test_wrap_should_not_be_available_until_logged_in():
    with pytest.raises(Forbidden):
        wrap_trusted_value_for_user('test')


@with_mocked_request(authenticated=False)
def test_unwrap_should_not_be_available_until_logged_in():
    with pytest.raises(Forbidden):
        unwrap_trusted_value_from_user('test')


@with_mocked_request()
def test_wrap_should_work_for_logged_in_user():
    res = wrap_trusted_value_for_user('test')
    assert isinstance(res, str)
    assert len(res) > 10


@with_mocked_request()
def test_wrap_unwrap_should_work_for_the_same_user():
    wrapped = wrap_trusted_value_for_user('test')
    unwrapped = unwrap_trusted_value_from_user(wrapped)
    assert unwrapped == "test"


@with_mocked_request()
def test_wrap_unwrap_should_work_for_long_data():
    data = """very long text very long textvery long text very long text very long text very long text
     very long text very long textvery long text very long textvery long text very long textvery long text very long text
     very long text very long textvery long text very long textvery long text very long textvery long text very long text
     very long text very long textvery long text very long textvery long text very long textvery long text very long text
     very long text very long textvery long text very long textvery long text very long text"""
    wrapped = wrap_trusted_value_for_user(data)
    unwrapped = unwrap_trusted_value_from_user(wrapped)
    assert unwrapped == data



def test_wrap_unwrap_should_not_work_for_changed_secret():
    wrap_unwrapped = wrap_trusted_value_for_user.__wrapped__
    unwrap_unwrapped = unwrap_trusted_value_from_user.__wrapped__
    wrapped = wrap_unwrapped('test', 0)
    unwrapped = unwrap_unwrapped(wrapped, 0)
    assert unwrapped == 'test'
    with pytest.raises(ValidationError):
        unwrapped = unwrap_unwrapped(wrapped, 1)
