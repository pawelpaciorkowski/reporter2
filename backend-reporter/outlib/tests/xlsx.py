import os
from outlib.xlsx import ReportXlsx
import pickle
import pathlib

test_data_path = os.path.join(pathlib.Path().resolve(), 'test_data')


def get_file_data(file_name: str):
    data_path = os.path.join(test_data_path, file_name)
    data = pickle.load(open(data_path, 'rb'))
    return data


def get_header_and_data_files(headers_file_name: str, data_file_name: str) -> tuple:
    headers = get_file_data(headers_file_name)
    data = get_file_data(data_file_name)
    return headers, data


def test_dzienna():
    headers, data = get_header_and_data_files(
        'hedery_dodatkowa_sprzedaz', 'dane_dodatkowa_sprzedaz')

    data['results'] = data['results'][1]
    testing = ReportXlsx(data).get_new_skipping(data['results']['header'])
    assert headers == testing


def test_eksport():

    headers, data = get_header_and_data_files(
        'hedery_export', 'dane_export')
    testing = ReportXlsx(data).get_new_skipping(data['results'][0]['header'])
    assert headers == testing


def test_max_coll():

    data = get_file_data('czasy_wykonan')
    details = data['results'][0]['header']
    report = ReportXlsx(data)
    testing = report._max_header_columns(details)
    assert testing == 16


def test_skipping_matrix():
    data = get_file_data('czasy_wykonan')
    details = data['results'][0]['header']
    report = ReportXlsx(data)
    testing = report._header_template(details)
    assert testing ==\
    [
    ['e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e'],
    ['e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e'],
    ['e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e', 'e']]


def test_sredni_czas_wykonania():
    data = get_file_data('czasy_wykonan')
    details = data['results'][0]['header']
    testing = ReportXlsx(data).get_new_skipping(details)
    expected_result = [
            ['v', 'v', 'v', 'v', '', '', '', '', 'v', 'v', 'v', '', '', '', '', 'v'],
            ['', '', '', 'v', 'v', '', '', '', '', '', 'v', 'v', '', '', '', ''],
            ['', '', '', 'v', 'v', 'v', 'v', 'v', '', '','v', 'v', 'v', 'v', 'v', '',]]
    assert testing == expected_result
