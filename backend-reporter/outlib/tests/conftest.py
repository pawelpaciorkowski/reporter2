import pytest

import datetime
from decimal import Decimal
from outlib.xlsx import ReportXlsx
from outlib.pdf import ReportPdf


@pytest.fixture(params=[ReportXlsx, ReportPdf])
def GeneratorClass(request):
    return request.param


@pytest.fixture
def sample_table_without_title():
    return {
        'type': 'table',
        'header': ['Col 1', 'Col 2', 'Col 3'],
        'data': [
            ['A1', 'B1', 'C1'],
            ['A2', 'B2', 'C2'],
            ['A3', 'B3', 'C3'],
        ]
    }


@pytest.fixture
def sample_table_with_title():
    res = sample_table_without_title.__wrapped__()
    res['title'] = 'Title zażółć gęślą jaźń'
    return res


@pytest.fixture
def sample_two_tables():
    tab1 = sample_table_with_title.__wrapped__()
    tab2 = sample_table_with_title.__wrapped__()
    tab1['title'] = 'Tabela 1'
    tab2['title'] = 'Tabela 2'
    return [tab1, tab2, {'type': 'info', 'text': 'Info 2 tabele'}]


@pytest.fixture
@pytest.mark.skip("""Ten test na razie nie przechodzi 
                     - w xlsx nie obsługujemy zbiorczego nagłówka o skomplikowanej strukturze""")
def sample_two_tables_with_complex_header():
    tab1 = sample_table_with_complex_header.__wrapped__()
    tab2 = sample_table_with_complex_header.__wrapped__()
    tab1['title'] = 'Tabela 1'
    tab2['title'] = 'Tabela 2'
    return [tab1, tab2]


@pytest.fixture
def sample_table_without_header():
    res = sample_table_without_title.__wrapped__()
    del res['header']
    return res


@pytest.fixture
def sample_table_with_complex_header():
    res = sample_table_without_title.__wrapped__()
    res['header'] = [
        [{'colspan': 3, 'title': 'Tabelka', 'fontstyle': 'bui'}],  # TODO: nie działa u - do sprawdzenia
        [{'rowspan': 2, 'title': 'Dwa wiersze', 'background': 'orange'}],
        ['Zwykły', {'title': 'Kolor', 'color': '#0000ff'}],
        [{'colspan': 2, 'title': 'podwójny nieostatni'}, {'fontstyle': 's', 'value': 'Skreślony'}]
    ]
    return res


@pytest.fixture
def sample_table_with_formatted_rows():
    res = sample_table_without_title.__wrapped__()
    res['data'][0][1] = None
    res['data'][1] = [
        {'fontstyle': 'bi', 'color': 'blue', 'value': 17},
        datetime.datetime.now(),
        {'background': 'yellow', 'value': Decimal("17.643")}
    ]
    return res


@pytest.fixture
def sample_table_with_complex_header2():
    res = sample_table_without_title.__wrapped__()
    res['header'] = [
        ['A', 'B', 'C'],
        [{'rowspan': 2, 'title': 'Dwa wiersze', 'background': 'orange'}],
        ['Zwykły', {'title': 'Kolor', 'color': '#0000ff'}],
        [{'colspan': 2, 'title': 'podwójny nieostatni'}, 'Zwykły']
    ]
    return res


@pytest.fixture
def sample_diagram_bars():
    return {
        'type': 'diagram',
        'subtype': 'bars',
        'x_axis_title': 'Oś odciętych',
        'y_axis_title': 'Oś rzędnych',
        'data': [
            [0, 5],
            [1, 4],
            [2, 3],
            [3, 2],
            [4, 1],
            [5, 0],
        ],
    }


@pytest.fixture
def sample_diagram_with_title():
    res = sample_diagram_bars.__wrapped__()
    res['title'] = 'Tytuł diagramu'
    return res


@pytest.fixture(params=['info', 'warning', 'error'])
def sample_infobox(request):
    return {
        'type': request.param,
        'text': '%s ZAŻÓŁĆ GĘŚLĄ JAŹŃ' % request.param
    }


@pytest.fixture
def sample_error():
    return {
        'type': 'error',
        'text': 'ERROR ZAŻÓŁĆ GĘŚLĄ JAŹŃ'
    }


@pytest.fixture(scope="session")
# taki fixture będzie utworzony raz na całą sesję testów
def all_samples():
    class DumbRequest:
        def __init__(self, param):
            self.param = param

    res = []

    def append_to_res(item):
        if isinstance(item, list):
            for subitem in item:
                append_to_res(subitem)
        else:
            res.append(item)

    for name, item in globals().items():
        if name.startswith('sample_') and hasattr(item, '__wrapped__'):
            if item._pytestfixturefunction.params is not None:
                for param in item._pytestfixturefunction.params:
                    append_to_res(item.__wrapped__(DumbRequest(param)))
            else:
                append_to_res(item.__wrapped__())
    return res


def all_samples_list():
    return all_samples.__wrapped__()
