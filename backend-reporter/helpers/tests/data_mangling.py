import pytest
import json
import datetime
from helpers.data_mangling import prepare_for_json


@pytest.fixture
def sample_datetime():
    return datetime.datetime(2019, 12, 27, 10, 11, 12)


def test_datetime_raises_exception(sample_datetime):
    data = {
        'date': sample_datetime
    }
    with pytest.raises(TypeError):
        json.dumps(data)

def test_datetime_formatting_for_json(sample_datetime):
    data = {
        'date': sample_datetime
    }
    json_data = json.dumps(prepare_for_json(data))
    json_loaded = json.loads(json_data)
    assert json_loaded['date'] == '2019-12-27 10:11'