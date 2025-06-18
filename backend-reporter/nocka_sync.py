import sys
from plugins import PluginManager
from helpers import Kalendarz
from datasources.nocka import NockaDatasource


def sync_wszystkie_laby_3_dni():
    pm = PluginManager()
    kal = Kalendarz()
    plugin = pm.find_plugin_by_path('meta.backend.nocka_sync')
    plugin.synchronizuj_dzien(kal.data('-4D'))
    plugin.synchronizuj_dzien(kal.data('-3D'))
    plugin.synchronizuj_dzien(kal.data('-2D'))
    plugin.synchronizuj_dzien(kal.data('-1D'))
    plugin.synchronizuj_snr()
    # TODO: dorobić drugą synchronizację dopisującą płatników na podstawie płatników marcelowych


def sync_wrzesien():
    pm = PluginManager()
    plugin = pm.find_plugin_by_path('meta.backend.nocka_sync')
    plugin.synchronizuj_dzien('2020-09-01')
    plugin.synchronizuj_dzien('2020-09-02')
    plugin.synchronizuj_dzien('2020-09-03')
    plugin.synchronizuj_dzien('2020-09-04')
    plugin.synchronizuj_dzien('2020-09-05')
    plugin.synchronizuj_dzien('2020-09-06')
    plugin.synchronizuj_dzien('2020-09-07')
    plugin.synchronizuj_dzien('2020-09-08')
    plugin.synchronizuj_dzien('2020-09-09')
    plugin.synchronizuj_dzien('2020-09-10')
    plugin.synchronizuj_dzien('2020-09-11')
    plugin.synchronizuj_dzien('2020-09-12')
    plugin.synchronizuj_dzien('2020-09-13')
    plugin.synchronizuj_snr()

def importuj_cennik_wzorcowy(fn):
    import openpyxl
    wb = openpyxl.load_workbook(fn)
    ws = wb.active
    values = []
    for row in ws:
        if row[0].value in (None, 'Symbol badania'):
            continue
        values.append({'badanie': row[0].value.upper().strip(), 'cena': row[1].value})
    ds = NockaDatasource(read_write=True)
    ds.execute("delete from cennik_wzorcowy")
    ds.multi_insert('cennik_wzorcowy', values)
    ds.commit()

if __name__ == '__main__':
    sync_wszystkie_laby_3_dni()

    # sync_wrzesien()
    # importuj_cennik_wzorcowy(sys.argv[1])