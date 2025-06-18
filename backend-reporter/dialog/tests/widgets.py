import pytest
import mock

from flask import app
import jwt
import werkzeug
from config import Config
from dialog import LabSelector
from test_utils import with_mocked_request, with_mocked_postgres

@with_mocked_request(authenticated=False)
def test_lab_selector_unauthenticated():
    ls = LabSelector(field='lab')
    params = {'lab': 'CZERNIA'}
    with pytest.raises(werkzeug.exceptions.Forbidden):
        ls.load_params(params)

@with_mocked_request()
@with_mocked_postgres()
def test_lab_selector_authenticated():
    ls = LabSelector(field='lab')
    params = {'lab': 'CZERNIA'}
    parsed = ls.load_params(params)
    assert parsed['lab'] == 'CZERNIA'


@pytest.mark.slow
# odpalać pytest -m slow żeby poszły tylko takie testy
# pytest -m "not slow" żeby takie nie poszły
@with_mocked_postgres()
@with_mocked_request()
def test_lab_selector_multivalues():
    ls = LabSelector(field='lab', multiselect=True)
    # ls.load_params()
    params = {'lab': 'CZERNIA KOPERNI'}
    parsed = ls.load_params(params)
    assert parsed['lab'] == ['CZERNIA', 'KOPERNI']


@with_mocked_postgres()
@with_mocked_request()
def test_lab_selector_multivalues_rights_cut():
    ls = LabSelector(field='lab', multiselect=True)
    # ls.load_params()
    params = {'lab': 'CZERNIA KOPERNI RUDKA'}
    parsed = ls.load_params(params)
    assert parsed['lab'] == ['CZERNIA', 'KOPERNI']


@with_mocked_postgres()
@with_mocked_request(rights='L-KIER:*')
def test_lab_selector_multivalues_rights_all():
    ls = LabSelector(field='lab', multiselect=True)
    # ls.load_params()
    params = {'lab': 'CZERNIA KOPERNI RUDKA'}
    parsed = ls.load_params(params)
    assert parsed['lab'] == ['CZERNIA', 'KOPERNI', 'RUDKA']


@with_mocked_postgres()
@with_mocked_request()
def test_lab_selector_multivalues_nonexistent_cut():
    ls = LabSelector(field='lab', multiselect=True)
    # ls.load_params()
    params = {'lab': 'CZERNIA PEKIN KOPERNI'}
    parsed = ls.load_params(params)
    assert parsed['lab'] == ['CZERNIA', 'KOPERNI']


# @pytest.mark.skip("Przykładowy pominięty test")
# może być też skipif(warunek, opis)
@with_mocked_postgres()
@with_mocked_request()
def test_lab_selector_authenticated_IGNORE():
    ls = LabSelector(field='lab')
    # ls.load_params()
    params = {'lab': 'CZERNIA'}
    parsed = ls.load_params(params)
    assert parsed['lab'] == 'CZERNIA'
