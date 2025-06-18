from raporty.Rozliczeniowe.zestawieniaSklep.utils.Query import QueryData


def test_params_to_tuple():
    params = {'dataod': '2016-04-01', 'datado': '2016-04-30'}
    assert QueryData._params_to_list(params, []) == ('2016-04-01', '2016-04-30')


def test_params_to_tuple_with_skip():
    params = {'dataod': '2016-04-01', 'datado': '2016-04-30'}
    assert QueryData._params_to_list(params, ['dataod']) == ('2016-04-30',)
