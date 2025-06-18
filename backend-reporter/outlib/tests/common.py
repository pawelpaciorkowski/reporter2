import pytest

from helpers import prepare_for_json
from .conftest import all_samples_list


def test_render_all_and_do_not_crash(GeneratorClass, all_samples):
    generator = GeneratorClass({
        'results': prepare_for_json(all_samples)
    })
    res = generator.render_as_bytes()
    assert len(res) > 100


@pytest.mark.parametrize("sample", all_samples_list())
def test_render_single_and_do_not_crash(GeneratorClass, sample):
    generator = GeneratorClass({
        'results': [prepare_for_json(sample)]
    })
    res = generator.render_as_bytes()
    assert len(res) > 100


def test_flat_table(GeneratorClass, sample_two_tables):
    generator = GeneratorClass({
        'results': sample_two_tables
    }, flat_table=True)
    res = generator.render_as_bytes()
    assert len(res) > 100


def test_report_params_errors(GeneratorClass, sample_table_with_title):
    generator = GeneratorClass({
        'results': [sample_table_with_title],
        'params': {
            'parametr1': 'Parametr 1',
            'parametr2': 'Teścik'
        },
        'errors': ['Sample error']
    })
    res = generator.render_as_bytes()
    assert len(res) > 100

def test_unknown_result_type(GeneratorClass):
    with pytest.raises(Exception):
        generator = GeneratorClass({
            'results': [
                {'type': 'foo', 'data': 'bar'}
            ]
        })
        res = generator.render_as_bytes()
