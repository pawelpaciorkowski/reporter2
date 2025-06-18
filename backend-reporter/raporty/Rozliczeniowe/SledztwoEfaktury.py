from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from datasources.snr import SNR
from datasources.efaktura import EFakturaDatasource
from api.common import get_db
from decimal import Decimal

MENU_ENTRY = 'Śledztwo efaktury'

REQUIRE_ROLE = ['C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Zestawienie wystawionych faktur w okresie, ze sprawdzeniem zestawień do efaktur'),
    LabSelector(multiselect=False, field='lab', title='Laboratorium', replikacja=True, symbole_snr=True),
    Switch(field='bez_labu', title='Faktury zbiorcze (bez laboratorium)'),
    DateInput(field='dataod', title='Data początkowa', default='PM'),
    DateInput(field='datado', title='Data końcowa', default='KM'),
))

SQL_FAKTURY_SNR = """
    select f.numer, f.typ, case when f.czykorekta != 0 then 'TAK' else '' end as korekta,
        f.odbiorca, pwl.symbol as "Symbol płatnika", pl.nazwa as "Nazwa płatnika", pl.nip, f.datadokumentu, 
        (select sum(pf.kwotanetto) from pozycjefaktur pf where pf.faktura=f.id and not pf.del) as netto, f.opis,
        case when pl.hs->'fakturyelektroniczne'='True' then 'TAK' else '' end as "Płatnik - efaktury", 
        pl.hs->'zestawienia' as "Płatnik - zestawienia", pl.hs->'eksporty' as "Płatnik - eksporty"
    from faktury f
    left join platnicy pl on pl.id=f.platnik
    left join platnicywlaboratoriach pwl on pwl.platnik=f.platnik and pwl.laboratorium=f.laboratorium
    where f.laboratorium=%s
    and f.datadokumentu between %s and %s and not f.del
    order by f.numer
"""

SQL_ZESTAWIENIA_SNR = """
    select z.symbol, z.nazwa, z.hs->'filename' as filename
    from zestawienia z where z.symbol=%s and not del
"""

SQL_EKSPORTY_SNR = """
    select z.symbol, z.nazwa, z.hs->'filename' as filename
    from eksporty z where z.symbol=%s and not del
"""

SQL_EFAKTURA = """
    select p.PaymentId as Payment, p.DateAdded as PaymentDateAdded,
           p.IsApproved, p.IsHIdden, p.IsPayed,
           at.Name as AttachmentType,
           a.FileName, a.DateAdded as AttachmentDateAdded, a.IsHidden
    from Payments p
    left join Attachments a on a.PaymentId=p.PaymentID
    left join AttachmentTypes at on at.TypeId=a.AttachmentTypeId
    where p.RefferenceName=%s
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['lab'] is None and not params['bez_labu']:
        raise ValidationError("Nie wybrano laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'zbierz_snr'
    }
    report.create_task(task)
    report.save()
    return report


def zbierz_snr(task_params):
    params = task_params['params']
    snr = SNR()
    efak = EFakturaDatasource()
    sql = SQL_FAKTURY_SNR
    sql_params = []
    if params['bez_labu']:
        sql = sql.replace('f.laboratorium=%s', 'f.laboratorium is null').replace('pwl.symbol', 'pl.symbole')
    else:
        sql_params.append(params['lab'])
    sql_params += [params['dataod'], params['datado']]
    cols, rows = snr.select(sql, sql_params)
    cols += ['EF utworzona', 'EF zaakceptowana', 'EF ukryta', 'EF zapłacona', 'EF załączniki']
    res = []
    wszystkie_zestawienia = {}
    wszystkie_eksporty = {}
    for row in rows:
        row = list(row)
        nr = row[0]
        jest_ef = row[10]
        zestawienia = [s for s in (row[11] or '').strip().split(' ') if s != '']
        eksporty = [s for s in (row[12] or '').strip().split(' ') if s != '']
        for symbol in zestawienia:
            if symbol not in wszystkie_zestawienia:
                wszystkie_zestawienia[symbol] = snr.dict_select(SQL_ZESTAWIENIA_SNR, [symbol])[0]
        for symbol in eksporty:
            if symbol not in wszystkie_eksporty:
                wszystkie_eksporty[symbol] = snr.dict_select(SQL_EKSPORTY_SNR, [symbol])[0]
        if jest_ef == 'TAK': # TODO - wg nazwy kolumny jakiś helper
            efcols, efrows = efak.select(SQL_EFAKTURA, [nr])
            if len(efrows) == 0:
                row += [{'background': '#ff0000', 'value': 'BRAK'}, '', '', '', '']
            else:
                row += [efrows[0][1], 'TAK' if efrows[0][2] else '', 'TAK' if efrows[0][3] else '', 'TAK' if efrows[0][4] else '']
                zal = []
                ile_zal = 0
                for efrow in efrows:
                    if efrow[5] == 'Other attachment' and not efrow[8]:
                        ile_zal += 1
                    zal.append('%s (utw %s%s)' % (
                        efrow[6],
                        efrow[7].strftime('%Y-%m-%d %H:%M'),
                        ', ukryty' if efrow[8] else ''
                    ))
                zal = '\n'.join(zal)
                cell = {'fontstyle': 'm', 'value': zal}
                if ile_zal != len(zestawienia) + len(eksporty):
                    cell['background'] = '#ff0000'
                row.append(cell)
        else:
            row += ['', '', '', '', '']
        res.append(row)
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(res)
    }
