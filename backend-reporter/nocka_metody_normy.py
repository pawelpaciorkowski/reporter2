import sentry_sdk
import sys
import time
import datetime
import traceback
import config
from plugins import PluginManager
from helpers import Kalendarz
from datasources.nocka import NockaDatasource
from threading import Thread, Lock
from multiprocessing import Pool

sentry_sdk.init(config.Config.SENTRY_URL)

log_lock = Lock()


def log(*args):
    with log_lock:
        line = ' '.join([str(arg) for arg in args]) + '\n'
        print(line)
        with open('/tmp/nocka_metody_i_normy.log', 'a') as f:
            f.write(line)


def do_work(system):
    pm = PluginManager()
    plugin = pm.find_plugin_by_path('meta.backend.nocka_sync')
    log(system, "START", datetime.datetime.now())
    start = time.time()
    try:
        ls = plugin.LabSynchroniser(system)
        ls.synchronizuj_metody_i_normy()
        end = time.time()
        log(system, "KONIEC, zajęło %d sekund" % int(end - start))
        return True
    except:
        sentry_sdk.capture_exception()
        end = time.time()
        log(system, "BŁĄD, zajęło %d sekund" % int(end - start))
        log(traceback.format_exc())
        return False


def wczytaj_normy():
    log("Start", datetime.datetime.now())
    wczoraj = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
    worklist = []
    nds = NockaDatasource()
    for row in nds.dict_select("select distinct system from log_synchronizacje where sync_date=%s and success",
                               [wczoraj]):
        if row['system'] in ['SIEDLCE', 'BELCHAT']:
            continue

        worklist.append(row['system'])
    worklist.append('LIMBACH')

    pool = Pool(4)
    results = pool.map(do_work, worklist)
    ile = ile_ok = 0
    for res in results:
        ile += 1
        if res:
            ile_ok += 1
    log("Koniec", datetime.datetime.now(), "%d / %d się udało" % (ile_ok, ile))


if __name__ == '__main__':
    wczytaj_normy()
