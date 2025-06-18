from helpers import prepare_for_json
from api.common import get_db
from tasks.db import redis_conn

MENU_ENTRY = 'Serwery'

GUI_MODE = 'one_shot'


def get_content(user_login):
    data = []
    with get_db() as db:
        for row in db.select('select * from laboratoria order by symbol'):
            system = row['symbol']
            redis_key_ok = 'baza:ok:%s' % system
            redis_key_ng = 'baza:ng:%s' % system
            b_ok = redis_conn.get(redis_key_ok) or b''
            b_ng = redis_conn.get(redis_key_ng) or b''
            s_ok = ''
            s_ng = ''
            bg = '#eee'
            fg = '#000'
            if row['adres_fresh'] is None or not row['aktywne']:
                fg = '#888'
            if b_ok != b'' and b_ok >= b_ng:
                bg = 'lightgreen'
            elif b_ng != b'' and (b_ok == b'' or b_ok < b_ng):
                bg = 'red'
            data.append([
                {'value': row['symbol'], 'fontstyle': 'bc', 'background': bg, 'color': fg},
                row['nazwa'], row['centrum_kosztow'], row['adres_fresh'],
                '✓' if row['aktywne'] else ' ',
                '✓' if row['laboratorium'] else ' ',
                '✓' if row['wewnetrzne'] else ' ',
                '✓' if row['zewnetrzne'] else ' ',
                '✓' if row['zewnetrzne_got'] else ' ',
                '✓' if row['pracownia_domyslna'] else ' ',
                '✓' if row['marcel'] else ' ',
                '✓' if row['replikacja'] else ' ',
                '✓' if row['baza_pg'] else ' ',
                b_ok, b_ng, s_ok, s_ng])
    return [
        {
            'type': 'table',
            'title': 'Serwery laboratoryjne',
            'header': ['Symbol', 'Nazwa', 'C.k.', 'VPN',
                       {'title': 'aktywne', 'dir': 'bt', 'fontstyle': 'b'},
                       {'title': 'laboratorium', 'dir': 'bt', 'fontstyle': 'b'},
                       {'title': 'wewnętrzne', 'dir': 'bt', 'fontstyle': 'b'},
                       {'title': 'zewnętrzne', 'dir': 'bt', 'fontstyle': 'b'},
                       {'title': 'zewnętrzne got.', 'dir': 'bt', 'fontstyle': 'b'},
                       {'title': 'prac. domyślna', 'dir': 'bt', 'fontstyle': 'b'},
                       {'title': 'marcel', 'dir': 'bt', 'fontstyle': 'b'},
                       {'title': 'replikacja', 'dir': 'bt', 'fontstyle': 'b'},
                       {'title': 'postgres', 'dir': 'bt', 'fontstyle': 'b'},
                       'Baza OK', 'Baza BŁĄD', 'SSH OK', 'SSH BŁĄD'],
            'data': prepare_for_json(data)
        }
    ]
