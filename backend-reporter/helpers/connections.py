from datasources.centrum import Centrum, CentrumConnectionError, CentrumManager
from datasources.snr import SNR
from datasources.bankkrwi import BankKrwiDatasource
from api.common import get_db
from tasks.db import redis_conn
from datetime import datetime
from config import Config
from pprint import pprint


def get_centra(system):
    with get_db() as db:
        return db.select("select * from laboratoria where symbol=%s", [system])


def get_db_engine(centra):
    if len(centra) == 0:
        return None
    if centra[0]['baza_pg']:
        return 'postgres'
    else:
        return 'firebird'


def get_centrum_instance(system, fresh=False, load_config=False, none_on_error=False):
    fs = '_fresh' if fresh else ''
    centra = get_centra(system)
    adres = centra[0]['adres' + fs]
    alias = centra[0]['baza' + fs]
    if not Config.SIEC_ALAB:
        if adres in ('192.168.5.105', '192.168.5.106'):
            adres = 'localhost'
    engine = get_db_engine(centra)
    cnt_manager = CentrumManager(adres=adres, alias=alias, engine=engine)
    cnt = cnt_manager.get_connection()

    # cnt = Centrum(adres=adres, alias=alias)

    testuj = True
    redis_key = 'baza:status:%s' % system
    redis_key_ok = 'baza:ok:%s' % system
    redis_key_ng = 'baza:ng:%s' % system
    ost_status = redis_conn.get(redis_key)
    if ost_status is not None:
        ost_status = ost_status.decode().split(' ')
        print(redis_key, ost_status)
        if ost_status[-1] == 'OK':
            testuj = False
        else:
            print('Połączenie ostatnio nieudane - poddajemy się bez sprawdzania')
            if none_on_error:
                return None
            else:
                raise CentrumConnectionError('Baza niedostępna - połączenie ostatnio nieudane', system, 2)
    if testuj:
        czas = datetime.now().strftime('%Y-%m-%d %H:%M')
        if cnt.ping():
            redis_conn.set(redis_key, czas + ' OK', ex=300)
            redis_conn.set(redis_key_ok, czas, ex=604800)
            print('Test połączenia - ok')
        else:
            redis_conn.set(redis_key, czas + ' NG', ex=300)
            redis_conn.set(redis_key_ng, czas, ex=604800)
            print('Test połączenia - nie udało się otworzyć portu')
            if none_on_error:
                return None
            else:
                raise CentrumConnectionError('Baza niedostępna - nie udało się otworzyć portu', system, 0)
    if cnt.system is None:
        cnt.system = system
    return cnt


def get_centrum_connection(system, fresh=False, load_config=False, none_on_error=False):
    cnt = get_centrum_instance(system, fresh, load_config, none_on_error)
    try:
        conn = cnt.connection()
        if load_config:
            conn.system_config = cnt.get_system_config()
    except Exception as e:
        if none_on_error:
            return None
        else:
            raise CentrumConnectionError(str(e), system, 1)
    return conn


def get_snr_connection():
    return SNR()


def get_bank_krwi_connection(system):
    with get_db() as db:
        laby = db.select("select * from laboratoria where symbol=%s", [system])
        if len(laby) == 0:
            return None
        lab = laby[0]
        if lab['adres_bank'] is None:
            return None
        return BankKrwiDatasource(system, lab['adres_bank'], lab['baza_bank'])


def get_db_engine_for_lab(lab):
    centra = get_centra(lab)
    return get_db_engine(centra)
