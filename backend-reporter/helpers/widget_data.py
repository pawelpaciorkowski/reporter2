from datasources.mop import MopDatasource
from datasources.reporter import ReporterDatasource
from datasources.centrum import CentrumWzorcowa
from datasources.snrkonf import SNRKonf
from datasources.sklep import SklepDatasource
from datasources.alabinfo import AlabInfoDatasource
from tasks.db import redis_conn
from api.auth.utils import login_required
from api.restplus import api
from plugins import ROLE_CONTAINMENT
import json

BRAK_ROLI = 'Brak (tylko pojedyńcze raporty)'


class WidgetDataProvider:
    def __init__(self, widget):
        self.widget = widget

    @login_required
    def lab_filter_for_user(self, user_permissions):
        # TODO: sprawdzać jeszcze na podstawie uprawnienia i pluginu
        res = []
        for perm, labs in user_permissions:
            if labs == '*':
                return None
            else:
                for lab in labs.split(' '):
                    if lab not in res:
                        res.append(lab)
        return res

    @login_required
    def role_filter_for_user(self, user_permissions):
        user_roles = [permission[0] for permission in user_permissions]
        available_roles = []
        for role in user_roles:
            available_roles += ROLE_CONTAINMENT.get(role)
        return available_roles

    def role_filter_no_ADMIN(self, roles):
        available_roles = []
        for role in roles:
            if role['symbol'] == 'ADMIN':
                continue
            available_roles.append(role)
        return available_roles

    def get_and_cache(self, ident, executor, timeout=300):
        ident = 'wdp:' + ident
        res = redis_conn.get(ident)
        if res is not None:
            return json.loads(res.decode())
        else:
            res = executor()
            redis_conn.set(ident, json.dumps(res), ex=timeout)
            return res

    def get_plugin(self):
        pass

    def get_data_laboratoria(self, widget, params):
        rd = ReporterDatasource()
        laboratoria = self.get_and_cache('laboratoria',
                                         lambda: ReporterDatasource().dict_select(
                                             "select * from laboratoria order by kolejnosc"))
        lab_filter = self.lab_filter_for_user()
        res = []
        show_only = widget.init_kwargs.get('show_only')
        symbol_col = 'symbol_snr' if widget.init_kwargs.get('symbole_snr', False) else 'symbol'
        if callable(show_only):
            show_only = show_only()
        for row in laboratoria:
            dodaj = True
            if lab_filter is not None and row[symbol_col] not in lab_filter:
                dodaj = False
            if show_only is not None and row[symbol_col] not in show_only:
                dodaj = False
            if widget.init_kwargs.get('pracownie_domyslne', False) and not row['pracownia_domyslna']:
                dodaj = False
            if widget.init_kwargs.get('wewnetrzne', False) and not row['wewnetrzne']:
                dodaj = False
            if widget.init_kwargs.get('replikacje', False) and not row['replikacja']:
                dodaj = False
            if widget.init_kwargs.get('bank_krwi', False) and row['adres_bank'] is None:
                dodaj = False
            if row['adres_fresh'] is None:
                dodaj = False
            if params is not None:
                search_string = "%s %s %s" % (row[symbol_col], row['nazwa'], row['adres_fresh'])
                if params.lower() not in search_string.lower():
                    dodaj = False
            if not row['aktywne'] and not widget.init_kwargs.get('pokaz_nieaktywne', False):
                dodaj = False
            if not row['baza_pg'] and widget.init_kwargs.get('tylko_postgres', False):
                dodaj = False
            if not row['symbol'].startswith('HIST') and widget.init_kwargs.get('tylko_histopatologia', False):
                dodaj = False
            if dodaj:
                res.append({'value': row[symbol_col], 'label': '%s - %s' % (row[symbol_col], row['nazwa'])})
        if widget.init_kwargs.get('alfabetycznie', False):
            res = sorted(res, key=lambda x: x['label'])
        return res

    def get_data_raporty(self, widget, params):
        data = []
        role = []

        for row in self.get_data_role(None, None):
            role.append({'symbol': row['value'], 'nazwa': row['label']})

        def check_if_katalog(module):
            if hasattr(module, 'LAUNCH_DIALOG'):
                return False
            return True

        def disable_for_catalog(data, is_katalog):
            if is_katalog:
                data['disabled'] = True
            else:
                data['disabled'] = False

        def zbierz_poziom(plugin, level=0):
            nazwa = plugin.get('menu_entry')
            path = plugin.get('path').replace('/', '.')
            module = plugin.get('module')
            if nazwa is not None:
                nazwa_ind = ('-' * (level - 1) * 4) + nazwa
                for rola in role:
                    upr = api.plugin_manager.can_access(rola['symbol'], path)
                    if upr:
                        wiersz = [path, {'value': nazwa_ind, 'fontstyle': 'b'}]
                        wiersz[1]['katalog'] = not api.plugin_manager.is_executable(module)
                        data.append(wiersz)
                        break
            if 'children' in plugin:
                for cld in plugin['children']:
                    zbierz_poziom(cld, level + 1)

        for podtyp in api.plugin_manager.plugin_packs:
            zbierz_poziom(api.plugin_manager.plugin_packs[podtyp])
        res = []
        for d in data:
            res.append({
                'value': d[0],
                'label': d[1]['value'],
                'disabled': d[1].get('katalog', False)})
        return res

    @login_required
    def get_data_kupony(self, widget, params, user_permissions):

        sklep = SklepDatasource()

        kody = sklep.dict_select(
            'select * from commerce_promotion_field_data order by name')
        res = []
        for row in kody:
            res.append({'value': str(row['promotion_id']),
                        'label': row['display_name']})
        return res
    
    @login_required
    def get_data_histo_uzytkownicy(self, widget, params, user_permissions):

        alabinfo = AlabInfoDatasource()

        uzytkownicy = alabinfo.dict_select(
            """select * from users where login is not null and login <> '' and user_group_id='2817' and active=True order by name""")
        res = []
        for row in uzytkownicy:
            res.append({'value': str(row['id']),
                        'label': row['name']})
        return res

    @login_required
    def get_data_role(self, widget, params, user_permissions):

        roles = ReporterDatasource().dict_select(
            'select * from role order by id')
        role_filter = self.role_filter_no_ADMIN(roles)
        res = []
        for row in role_filter:
            dodaj = True
            if dodaj:
                res.append({'value': row['symbol'],
                            'label': '%s - %s' % (
                                row['symbol'], row['nazwa'])})

        res.insert(0, {'value': BRAK_ROLI, 'label': BRAK_ROLI})
        return res

    @login_required
    def get_data_posiadane_dostepy(self, widget, params, user_id):

        roles = ReporterDatasource().dict_select(
            'select * from role order by id')
        role_filter = self.role_filter_no_ADMIN(roles)
        res = []
        for row in role_filter:
            dodaj = True
            if dodaj:
                res.append({'value': row['symbol'],
                            'label': '%s - %s' % (
                                row['symbol'], row['nazwa'])})

        res.insert(0, {'value': BRAK_ROLI, 'label': BRAK_ROLI})
        return res

    def get_data_platnicy(self, widget, params):
        snk = SNRKonf()
        search_params = {
            'type': 'platnicy',
            'query': params,
            'lab_filter': self.lab_filter_for_user(),
            'single_lab': None,
            'return_symbol': False
            # TODO: obsługa powyższych w zależności od ustawień widgeta
        }
        return snk.szukaj_podmiotow(search_params)

    def get_data_zleceniodawcy(self, widget, params):
        snk = SNRKonf()
        search_params = {
            'type': 'zleceniodawcy',
            'query': params,
            'lab_filter': self.lab_filter_for_user(),
            'single_lab': None,
            'return_symbol': False
            # TODO: obsługa powyższych w zależności od ustawień widgeta
        }
        return snk.szukaj_podmiotow(search_params)

    def get_data_pracownie(self, widget, params):
        def pracownie_wysylkowe():
            cnt = CentrumWzorcowa()
            with cnt.connection() as conn:
                res = []
                cols, rows = conn.raport_z_kolumnami("""
                    select p.symbol as SYMBOL, p.nazwa as NAZWA from pracownie p 
                        left outer join grupypracowni gp on gp.id=p.grupa
                        left outer join systemy s on p.system=s.id
                        where p.del = 0 and gp.symbol in ('ZEWN', 'ALAB') order by p.symbol;
                """)
                for row in rows:
                    res.append({'value': row[0].strip(), 'label': '%s - %s' % (row[0].strip(), row[1])})
                return res

        if widget.init_kwargs.get('wariant') == 'wysylkowe':
            return self.get_and_cache('pracownie__wysylkowe', pracownie_wysylkowe, 3600)
        else:
            raise Exception('get_data_pracownie: nieprawidłowy wariant')

    def get_data_punkty(self, widget, params):
        mop = MopDatasource()
        lab_filter = self.lab_filter_for_user()
        punkty = mop.get_cached_data('api/v2/collection-point')
        res = []
        for punkt in punkty:
            if punkt.get('laboratory') is None or not punkt.get('isActive'):
                continue
            lab = punkt.get('laboratory', {}).get('symbol', '')
            if lab != '' and (lab_filter is None or lab in lab_filter):
                search_string = punkt.get('name', '') + ' ' + punkt.get('marcel', '') + punkt.get('street', '') + \
                                (punkt.get('city') or {})['name']
                if params.lower() in search_string.lower():
                    nazwa = punkt['name'] or ''
                    if nazwa == '':
                        nazwa = (punkt.get('city') or {})['name'] + ' ' + punkt.get('street', '')
                    res.append(
                        {'value': punkt['marcel'], 'label': '%s - %s' % (punkt['marcel'], nazwa)}
                    )
        return res

    def get_data_badania(self, widget, params):
        snr = SNRKonf()
        return snr.szukaj_badan(params)

    def get_widget_data(self, widget, params):
        if self.widget.datasource == 'laboratoria':
            return self.get_data_laboratoria(widget, params)
        elif self.widget.datasource == 'platnicy':
            return self.get_data_platnicy(widget, params)
        elif self.widget.datasource == 'zleceniodawcy':
            return self.get_data_zleceniodawcy(widget, params)
        elif self.widget.datasource == 'pracownie':
            return self.get_data_pracownie(widget, params)
        elif self.widget.datasource == 'posiadane_dostepy':
            return self.get_data_posiadane_dostepy(widget, params)
        elif self.widget.datasource == 'role':
            return self.get_data_role(widget, params)
        elif self.widget.datasource == 'raporty':
            return self.get_data_raporty(widget, params)
        elif self.widget.datasource == 'punkty':
            return self.get_data_punkty(widget, params)
        elif self.widget.datasource == 'badania':
            return self.get_data_badania(widget, params)
        elif self.widget.datasource == 'kupony':
            return self.get_data_kupony(widget, params)
        elif self.widget.datasource == 'histo_uzytkownicy':
            return self.get_data_histo_uzytkownicy(widget, params)
        return {'error': 'Nieznane źródło danych %s' % self.widget.datasource}
