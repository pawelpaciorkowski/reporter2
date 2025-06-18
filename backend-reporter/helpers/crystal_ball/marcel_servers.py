KATALOG_ZDALNY_DOMYSLNY = '/var/sig/Wydrukowane/'

KATALOGI_ZDALNE = {
    'CZERNIA': '/var/sig/data-NIE_KASOWAC/Wydrukowane/',
    'HISTOPA': '/var/sig/data-HIST/Wydrukowane',
    'HISTJAN': '/var/sig/data-Hist/Wydrukowane',
    'LIMBACH': '/home/lab/Marcel/Podpis/data/Wydrukowane',
}


def katalog_wydrukow(system):
    return KATALOGI_ZDALNE.get(system, KATALOG_ZDALNY_DOMYSLNY)


def sciezka_wydruku(system, data_zlecenia, numer_zlecenia, plik):
    sciezka = katalog_wydrukow(system)
    sciezka += data_zlecenia.strftime('/%Y%m/%d/')
    sciezka += ('%04d' % numer_zlecenia)[:4] + '/'
    sciezka += plik
    return sciezka