import sys
import time
import datetime
from plugins import PluginManager
from helpers import Kalendarz
from datasources.nocka import NockaDatasource


def log(*args):
    line = ' '.join([str(arg) for arg in args]) + '\n'
    print(line)
    with open('/tmp/nocka_uzupelnij.log', 'a') as f:
        f.write(line)

def uzupelniaj_luki():
    start = time.time()
    kal = Kalendarz()
    pm = PluginManager()
    plugin = pm.find_plugin_by_path('meta.backend.nocka_sync')
    przerwij = '2020-09-02'
    kal.ustaw_teraz('2019-12-31')
    log('=== START', datetime.datetime.now())
    while time.time() - start < 7200 and kal.data('T') != przerwij:
        dzien = kal.data('+1D')
        log('Synchronizacja', dzien)
        dzien_start = time.time()
        plugin.synchronizuj_dzien(dzien)
        log('Koniec', dzien, '- zajęło %d s' % (time.time() - dzien_start))
        kal.ustaw_teraz(dzien)
    log('=== KONIEC labów, doszło do', kal.data('T'), datetime.datetime.now())
    # plugin.synchronizuj_snr()
    log('=== KONIEC SNR', datetime.datetime.now())


def akcja_uzupelniania():
    start = time.time()
    pm = PluginManager()
    plugin = pm.find_plugin_by_path('meta.backend.nocka_sync')
    cos_do_zrobienia = True
    log('=== uzup START', datetime.datetime.now())
    while time.time() - start < 7200 and cos_do_zrobienia:
        log('Akcja')
        dzien_start = time.time()
        cos_do_zrobienia = plugin.akcja_uzupelniania()
        log(' - zajęło %d s' % (time.time() - dzien_start))
    log('=== uzup KONIEC', datetime.datetime.now())


def uzupelnianie_wynikow():
    pm = PluginManager()
    plugin = pm.find_plugin_by_path('meta.backend.nocka_sync')
    rob = True
    start = time.time()
    while rob and time.time() - start < 7200:
        p_start = time.time()
        rob = plugin.uzupelniaj_wyniki()
        print('zajęło %d s' % (time.time() - p_start))

def wczytaj_normy():
    pm = PluginManager()
    plugin = pm.find_plugin_by_path('meta.backend.nocka_sync')
    nds = NockaDatasource()
    for row in nds.dict_select("select distinct system from log_synchronizacje where sync_date='2024-01-28' and success"):
        print(row['system'])
        # if row['system'] not in ('LUBLINC',):
        #     continue
        ls = plugin.LabSynchroniser(row['system'])
        ls.synchronizuj_metody_i_normy()
    ls = plugin.LabSynchroniser('LIMBACH')
    ls.synchronizuj_metody_i_normy()

if __name__ == '__main__':
    # akcja_uzupelniania()
    wczytaj_normy()
    # uzupelnianie_wynikow()
