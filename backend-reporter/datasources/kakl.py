from urllib.parse import quote_plus
from config import Config
from helpers import aes_encode
from datasources.postgres import PostgresDatasource
import requests
import time


def karta_klienta(platnik=None, zleceniodawca=None):
    # TODO: oddzielne żądanie dla zleceniodawcy - zmiana parametrów
    # url = 'https://kartaklienta.twojewyniki.com.pl:81/kakl/karta_snr/?request='
    url = 'https://11.1.1.64:81/kakl/karta_snr/?request='
    request = {
        'timestamp': time.time(),
        'snr_id': platnik
    }
    url += quote_plus(aes_encode(request, Config.DJALAB_KEY).encode())
    res = requests.get(url, verify=False)
    if '<table' not in res.text:
        return None
    return res.text


class KaKlDatasource(PostgresDatasource):
    def __init__(self):
        PostgresDatasource.__init__(self, "dbname='djalab' user='djalab_ro' password='djalab_ro' host='11.1.1.64' port=5432")


if __name__ == '__main__':
    print(karta_klienta('WZORC.1708522'))
