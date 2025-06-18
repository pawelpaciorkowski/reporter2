import pickle
import os
from helpers import prepare_for_json
from outlib.pdf import ReportPdf


def test_landscape(sample_two_tables):
    generator = ReportPdf({
        'results': sample_two_tables
    }, landscape=True)
    res = generator.render_as_bytes()
    assert len(res) > 100


# Testy w oparciu o prawdziwe dane
# def save_to_temp_htm(data):
#     with open('/home/kamil/Projects/reporter/backend-reporter/outlib/tests/test_data/temp.html', 'w') as f:
#         f.write(data)
#
#
# def test_nested_table():
#     with open('/home/kamil/Projects/reporter/backend-reporter/outlib/tests/test_data/zestawienie_dzienne_data', 'rb') as f:
#         data = pickle.load(f)
#
#     with open('/home/kamil/Projects/reporter/backend-reporter/outlib/tests/test_data/zestawienie_dzienne_old.html', 'r') as f:
#         result = f.read()
#
#     r = ReportPdf(None)
#     r._render_table(data['results'][0])
#     save_to_temp_htm(r.html)
#     assert str(r.html) == str(result)
#
#
# def test_simple_table():
#     with open('/home/kamil/Projects/reporter/backend-reporter/outlib/tests/test_data/data', 'rb') as f:
#         data = pickle.load(f)
#
#     with open('/home/kamil/Projects/reporter/backend-reporter/outlib/tests/test_data/simple_table_result.html', 'r') as f:
#         result = f.read()
#
#     r = ReportPdf(None)
#     r._render_table(data['results'][2])
#
#     assert str(r.html) == str(result)


def test_cell_depth():
    simple_list = [1, 2, 3]
    assert ReportPdf._cell_depth(1) == 1
    assert len(simple_list) == ReportPdf._cell_depth(simple_list)


def test_is_list():
    assert ReportPdf._is_list(1) is False
    assert ReportPdf._is_list([1, 2]) is True


def test_is_nested_cell():
    max_depth = 5
    cell = [1, 2, 3, 4, 5]
    assert ReportPdf._is_nested_cell(cell, max_depth) is True
    assert ReportPdf._is_nested_cell([1, 3], max_depth) is False
    assert ReportPdf._is_nested_cell(1, max_depth) is False


# TODO test ze stylami
def test_add_style():
    style = " red "
    assert ReportPdf._add_style(style) == '<td%ROWSPAN%>%VALUE%</td>'


def test_add_row_span():
    td = '<td%ROWSPAN%>%VALUE%</td>'
    cell = [1, 2]
    max_depth = 2
    assert ReportPdf._add_row_span(cell, max_depth, td, True) == '<td>%VALUE%</td>'
    assert ReportPdf._add_row_span(1, max_depth, td, False) == '<td rowspan="2" >%VALUE%</td>'


def test_find_max_nested_rows():
    arr = [
        [1],
        [1, 2],
        [1, 2, 3]
    ]
    assert ReportPdf._find_max_nested_rows(arr) == 3


def test_nested_rows():

    data = [
        [1, [11, 12]],
        [1, [11, 12]],
        [1, 11, [12, 13, 14]],
    ]
    display_report_data = {
        'type': 'table',
        # 'title': report_data.title,
        'header': ['col1', 'col2'],
        'data': prepare_for_json(data),
    }
    data = {
        'results': [display_report_data],
        'actions': ['xlsx', 'pdf', 'csv'],
        'errors': [],
        'progress': 1
    }
    direc = os.path.dirname(__file__)
    res = '<table class="reportTable"><thead><tr><th>col1</th><th>col2</th></tr></thead><tbody><tr><td rowspan="2" >1</td><td>11</td></tr><tr><td>12</td></tr><tr><td rowspan="2" >1</td><td>11</td></tr><tr><td>12</td></tr><tr><td rowspan="3" >1</td><td rowspan="3" >11</td><td>12</td></tr><tr><td>13</td></tr><tr><td>14</td></tr></tbody></table>'
    path = os.path.join(direc, 'test.html')
    html = ReportPdf(data)
    html._render_table(display_report_data)
    assert html.html == res

