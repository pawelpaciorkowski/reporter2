import datetime
import time
import hashlib
from api.auth import login_required
from datasources.snr import SNR
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError, Switch
from helpers.validators import validate_date_range, validate_symbol
from datasources.reporter import ReporterExtraDatasource
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, odpiotrkuj, list_from_space_separated

MENU_ENTRY = 'Przenoszenie klientów między bazami'

REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""
Wybierz laboratorium źródłowe i docelowe. Podaj symbole całych płatników do przeniesienia i/lub pojedynczych zleceniodawców.
Zleceniodawców gotówkowych można przenosić tylko posługując się symbolami zleceniodawców.
Po pierwszym uruchomieniu dane zostaną zweryfikowane, podana zostanie lista zmian do naniesienia w SNR i kod potwierdzenia.
Podanie kodu potwierdzenia przy kolejnym uruchomieniu jest niezbędne do właściwego naniesienia zmian.
    """),
    LabSelector(field='srclab', title='Lab źródłowy', pokaz_nieaktywne=True),
    LabSelector(field='dstlab', title='Lab docelowy'),
    TextInput(field='symbolep', title='Symbole płatników do przeniesienia w całości', textarea=True),
    TextInput(field='symbolez', title='Symbole pojedynczych zleceniodawców', textarea=True),
    TextInput(field='confirm', title='Kod potwierdzenia'),
    Switch(field='unikalnynip', title='Nie zakładaj płatnika jeśli płatnik z podanym NIP już istnieje'),
    Switch(field='unikalnynipzl', title='Nie zakładaj zleceniodawców dla płatników z istniejącym NIP'),
    Switch(field='obcinaj', title='Obcinaj symbole jeśli nie mieszczą się w 7 znakach'),
))


def start_report(params):
    @login_required
    def get_login(user_login):
        return user_login

    params = LAUNCH_DIALOG.load_params(params)
    params['login'] = get_login()
    for fld in ('symbolep', 'symbolez'):
        params[fld] = list_from_space_separated(params[fld], upper=True, also_comma=True, also_newline=True,
                                                also_semicolon=True, unique=True)
        for symbol in params[fld]:
            validate_symbol(symbol)
    if params['srclab'] == params['dstlab']:
        raise ValidationError("Laboratorium docelowe równe źródłowemu :(")
    if params['unikalnynipzl'] and not params['unikalnynip']:
        raise ValidationError("Nie da się tak")
    report = TaskGroup(__PLUGIN__, params)
    report.create_task({
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_zrob',
    })
    report.save()
    return report


def raport_zrob(task_params):
    params = task_params['params']
    errors = []
    warnings = []
    infos = []
    breaking_error = False
    kod_potw = None
    snr = SNR()
    lab_src = params['srclab']
    lab_dst = params['dstlab']
    obcinaj = params['obcinaj']
    inne_prefiksy = []
    lab_src_prefix = lab_dst_prefix = None
    for row in snr.dict_select("select symbol, hs->'przedrosteksymbolu' as prefix from laboratoria where not del"):
        if row['symbol'] == lab_src:
            lab_src_prefix = row['prefix']
        elif row['symbol'] == lab_dst:
            lab_dst_prefix = row['prefix']
        elif not empty(row['prefix']):
            inne_prefiksy.append(row['prefix'])
    if empty(lab_src_prefix) or empty(lab_dst_prefix):
        errors.append("Brak przedrostka dla labu źródłowego lub docelowego")
        breaking_error = True
    pwl_src = {}
    zwl_src = {}
    pwl_dst = {}
    zwl_dst = {}
    symbole_zl_dst = {}
    nipy_platnikow = {}
    platnicy_dst_nipow = {}
    platnicy_zleceniodawcow = {}
    zleceniodawcy_platnikow = {}
    grupy_platnikow = {}
    src_gotowka = dst_gotowka = None
    pwl_zaloz = [] # symbol, platnik, grupa
    gotowkowi_zaloz = {} # symbol docelowy -> dane
    zwl_zaloz = [] # symbol, zleceniodawca
    if not breaking_error:
        for lab, pwl_tab, zwl_tab in (
            [lab_src, pwl_src, zwl_src],
            [lab_dst, pwl_dst, zwl_dst]
        ):
            for row in snr.dict_select(
                """select trim(zwl.symbol) as symbol, zwl.platnik, zwl.hs->'grupa' as grupa, pl.nip 
                from platnicywlaboratoriach zwl 
                left join platnicy pl on pl.id=zwl.platnik
                where zwl.laboratorium=%s and not zwl.del""",
                [lab]
            ):
                pwl_tab[row['symbol']] = row['platnik']
                grupy_platnikow[row['symbol']] = row['grupa']
                nipy_platnikow[row['symbol']] = row['nip']
                if lab == lab_dst and not empty(row['nip']):
                    platnicy_dst_nipow[row['nip']] = row['symbol']
                if 'GOTOW' in row['symbol']:
                    if lab == lab_src:
                        if src_gotowka is None:
                            src_gotowka = row['symbol']
                        else:
                            errors.append("Powtórzony płatnik gotówkowy %s (%s)" % (row['symbol'], src_gotowka))
                            breaking_error = True
                    if lab == lab_dst:
                        if dst_gotowka is None:
                            dst_gotowka = row['symbol']
                        else:
                            errors.append("Powtórzony płatnik gotówkowy %s (%s)" % (row['symbol'], dst_gotowka))
                            breaking_error = True
            for row in snr.dict_select("""
                select trim(zwl.symbol) as symbol, zwl.zleceniodawca as zleceniodawca,
                    trim(pwl.symbol) as platnik
                from zleceniodawcywlaboratoriach zwl
                left join zleceniodawcy zl on zl.id=zwl.zleceniodawca
                left join platnicy pl on pl.id=zl.platnik
                left join platnicywlaboratoriach pwl on pwl.laboratorium=zwl.laboratorium and pwl.platnik=pl.id and not pwl.del 
                where zwl.laboratorium=%s and not zwl.del
            """, [lab]):
                zwl_tab[row['symbol']] = row['zleceniodawca']
                platnicy_zleceniodawcow[row['symbol']] = row['platnik']
                if row['platnik'] not in zleceniodawcy_platnikow:
                    zleceniodawcy_platnikow[row['platnik']] = []
                zleceniodawcy_platnikow[row['platnik']].append(row['symbol'])
                if lab == lab_dst:
                    symbole_zl_dst[row['zleceniodawca']] = row['symbol']
    def zaloz_platnika(symbol, ist_error=False):
        if not symbol.startswith(lab_src_prefix):
            errors.append("Symbol płatnika %s nie pasuje do prefiksu labu źrodłowego %s" % (symbol, lab_src_prefix))
        dst_symbol = lab_dst_prefix + symbol[len(lab_src_prefix):]
        if obcinaj:
            dst_symbol = dst_symbol[:7]
        if len(dst_symbol) > 7:
            errors.append("Symbol docelowy %s ma ponad 7 znaków" % dst_symbol)
        elif symbol not in pwl_src:
            errors.append("Płatnik %s nie istnieje w laboratorium źródłowym" % symbol)
        elif dst_symbol in pwl_dst:
            if not ist_error:
                return dst_symbol
            errors.append("Płatnik %s już istnieje" % dst_symbol)
        elif 'GOTOW' in symbol:
            errors.append("Nie da się przenieść płatnika gotówkowego %s" % symbol)
        else:
            if params['unikalnynip'] and not empty(nipy_platnikow[symbol]):
                if nipy_platnikow[symbol] in platnicy_dst_nipow:
                    res_platnik = platnicy_dst_nipow[nipy_platnikow[symbol]]
                    warnings.append("Nie założę płatnika %s na podstawie %s bo już istnieje płatnik %s z NIP %s" % (
                        dst_symbol, symbol, res_platnik, nipy_platnikow[symbol]
                    ))
                    if params['unikalnynipzl']:
                        return None
                    else:
                        return res_platnik
            grupa = grupy_platnikow[symbol]
            if grupa is not None:
                grupa = lab_dst_prefix + grupa[len(lab_src_prefix):]
            if grupa is not None and len(grupa) > 7:
                errors.append("Za długi symbol grupy płatnika %s" % grupa)
            else:
                for ist_symbol, ist_id in pwl_dst.items():
                    if ist_id == pwl_src[symbol]:
                        if ist_error:
                            errors.append("Nie można założyć płatnika %s bo jest już założony pod symbolem %s" % (dst_symbol, ist_symbol))
                            return None
                        else:
                            warnings.append("Nie można założyć płatnika %s bo jest już założony pod symbolem %s" % (dst_symbol, ist_symbol))
                        return ist_symbol
                pwl_zaloz.append(
                    (dst_symbol, pwl_src[symbol], grupa)
                )
                pwl_dst[dst_symbol] = pwl_src[symbol]
                infos.append("Płatnik do założenia %s" % dst_symbol)
                for zlec in zleceniodawcy_platnikow[symbol]:
                    if zlec not in params['symbolez']:
                        params['symbolez'].append(zlec)
                return dst_symbol

    for symbol in params['symbolep']:
        zaloz_platnika(symbol, ist_error=True)
    powt_zleceniodawcy = set()
    for symbol in params['symbolez']:
        dst_symbol = lab_dst_prefix + symbol[len(lab_src_prefix):]
        if obcinaj:
            dst_symbol = dst_symbol[:7]
        if len(dst_symbol) > 7:
            warnings.append("Symbol zleceniodawcy %s jest za długi" % dst_symbol)
        elif dst_symbol in powt_zleceniodawcy:
            warnings.append("Symbol zleceniodawcy %s powtórzyłby się" % dst_symbol)
        elif not symbol.startswith(lab_src_prefix):
            errors.append("Symbol zleceniodawcy %s nie pasuje do prefiksu labu źrodłowego %s" % (symbol, lab_src_prefix))
        elif symbol not in zwl_src:
            errors.append("Zleceniodawca %s nie istnieje w laboratorium źródłowym" % symbol)
        elif dst_symbol in zwl_dst:
            warnings.append("Zleceniodawca %s już istnieje" % dst_symbol)
        else:
            powt_zleceniodawcy.add(dst_symbol)
            platnik = platnicy_zleceniodawcow[symbol]
            dst_platnik = lab_dst_prefix + platnik[len(lab_src_prefix):]
            if len(dst_platnik) > 7:
                if obcinaj:
                    dst_platnik = dst_platnik[:7]
                else:
                    errors.append("Symbol płatnika %s za długi" % dst_platnik)
                    continue
            dst_zleceniodawca = zwl_src[symbol]
            if platnik not in params['symbolep']:
                if 'GOTOW' in platnik:
                    dst_platnik = dst_gotowka
                    for row in snr.dict_select("select * from zleceniodawcy where id=%s", [zwl_src[symbol]]):
                        for fld in 'id mid dc st del pc'.split(' '):
                            del row[fld]
                        row['pc'] = 'ALAB.1.720555798'
                        gotowkowi_zaloz[dst_symbol] = row
                    infos.append("Nowy zleceniodawca gotówkowy %s do założenia" % (dst_symbol,))
                    zwl_zaloz.append(
                        (dst_symbol, 'DOZAL:%s' % dst_symbol)
                    )
                    continue
                elif dst_platnik in pwl_dst:
                    pass
                else:
                    dst_platnik = zaloz_platnika(platnik, ist_error=False)
            if dst_platnik is not None:
                if dst_zleceniodawca not in symbole_zl_dst:
                    infos.append("Zleceniodawca %s (płatnik %s) do założenia" % (dst_symbol, dst_platnik))
                    zwl_zaloz.append(
                        (dst_symbol, dst_zleceniodawca)
                    )
                else:
                    warnings.append("Nie można założyć zleceniodawcy %s (płatnika %s), bo ma już założony symbol %s" % (
                        dst_symbol, dst_platnik, symbole_zl_dst[dst_zleceniodawca]
                    ))
            else:
                warnings.append("Nie można założyć zleceniodawcy %s bo nie został założony/znaleziony płatnik" % dst_symbol)
    res = []
    kod_potw = hashlib.sha256(repr((pwl_zaloz, zwl_zaloz)).encode()).hexdigest()

    if not empty(params['confirm']) and params['confirm'] != kod_potw:
        errors.append("Nieprawidłowy kod potwierdzenia!")
    if len(errors) > 0:
        for err in errors:
            res.append({ 'type': 'error', 'text': err })
    else:
        if empty(params['confirm']):
            if kod_potw == '1391876e63685b7da0e6a923dc6c4c106590930a70cdf4665088614cae243c44':
                infos.append('Nie ma nic do zrobienia')
            else:
                infos.append('Powyższe zmiany nie zostały naniesione na SNR. Aby je nanieść, wprowadź kod potwierdzenia: %s' % kod_potw)
        elif params['confirm'] == kod_potw:
            # pwl_zaloz = []  # symbol, platnik, grupa
            # gotowkowi_zaloz = {} # symbol docelowy => dane
            # zwl_zaloz = []  # symbol, zleceniodawca
            zalozeni = {}
            for symbol, platnik, grupa in pwl_zaloz:
                snr.insert('platnicywlaboratoriach', {
                    'pc': 'ALAB.1.720555798',
                    'laboratorium': lab_dst,
                    'platnik': platnik,
                    'symbol': symbol,
                    'hs': '"grupa"=>"%s"' % grupa
                })
            for symbol, row in gotowkowi_zaloz.items():
                new_id = snr.insert('zleceniodawcy', row)
                if new_id is None:
                    raise RuntimeError("Nie założył się zleceniodawca", row)
                zalozeni[symbol] = new_id
            for symbol, zleceniodawca in zwl_zaloz:
                if zleceniodawca.startswith('DOZAL:'):
                    zleceniodawca = zalozeni[zleceniodawca.split(':')[1]]
                snr.insert('zleceniodawcywlaboratoriach', {
                    'pc': 'ALAB.1.720555798',
                    'laboratorium': lab_dst,
                    'zleceniodawca': zleceniodawca,
                    'symbol': symbol,
                })
            snr.commit()
        else:
            raise RuntimeError("Niepusty i nieprawidłowy kod potwierdzenia")
    for warning in warnings:
        res.append({'type': 'warning', 'text': warning})
    for info in infos:
        res.append({'type': 'info', 'text': info})
    return res