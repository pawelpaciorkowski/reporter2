from helpers import prepare_for_json
from api.common import get_db
from api.restplus import api

MENU_ENTRY = 'Uprawnienia'
REQUIRE_ROLE = ['C-CS', 'R-CS']
GUI_MODE = 'one_shot'

def get_content(user_login):
    data = []
    role = []

    with get_db() as db:
        for row in db.select('select * from role order by symbol'):
            role.append({'symbol': row['symbol'], 'nazwa': row['nazwa']})

    def zbierz_poziom(plugin, level=0):
        nazwa = plugin.get('menu_entry')
        path = plugin.get('path').replace('/', '.')
        if nazwa is not None:
            nazwa_ind = ('\u00a0' * level * 4) + nazwa
            wiersz = [path, {'value': nazwa_ind, 'fontstyle': 'b'}]
            wiersz.append({
                'value': '✓' if hasattr(plugin['module'], 'LAUNCH_DIALOG') else '',
                'fontstyle': 'c',
            })
            for rola in role:
                upr = api.plugin_manager.can_access(rola['symbol'], path)
                wiersz.append({
                    'value': '✓' if upr else '',
                    'fontstyle': 'bc',
                    'hint': '%s - %s' % (rola['symbol'], nazwa)
                })
            data.append(wiersz)
        if 'children' in plugin:
            for cld in plugin['children']:
                zbierz_poziom(cld, level+1)
    for podtyp in api.plugin_manager.plugin_packs:
        zbierz_poziom(api.plugin_manager.plugin_packs[podtyp])
    header = ['Plugin', 'Menu', 'Dialog']
    for rola in role:
        header.append({'title': rola['nazwa'], 'fontstyle': 'b',
                       'hint': rola['symbol'], 'dir': 'bt'})

    results = [
        {
            'type': 'table',
            'title': 'Uprawnienia do modułów systemu',
            'header': header,
            'data': prepare_for_json(data)
        }
    ]

    return results

    # TODO: tak to nie zadziała, a też powinno na one-shot-report
    # return {
    #     'results': results,
    #     'actions': ['xlsx']
    # }
