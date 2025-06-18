import datetime
import os

from datasources.simple import SimpleDatasource

import base64
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError, Select
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection, slugify
from helpers.files import random_path
from datasources.simple import SimpleDatasource
from datasources.snr import SNR
from decimal import Decimal
from weasyprint import HTML
from outlib.xlsx import ReportXlsx

MENU_ENTRY = 'Drukowanie naklejek na faktury'

REQUIRE_ROLE = ['C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    Select(field="src", title="Źródło faktur", values={'simple': 'Simple', 'snrf': 'SNR faktury', 'snrr': 'SNR rozliczenia'}, default='simple'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
    TextInput(field='stanowisko', title='Stanowisko sprzedaży (Simple)'),
    TextInput(field='lab', title='Symbol laboratorium (SNR)'),
), hide_download=True)

SQL_SIMPLE = """
    select count(a.dok_idm) as iledok, a.odbiorca_id, i.stwystfakt_ids Stanowisko_sprzedaży,i.nazwa Nazwa_stanowiska_sprzedaży,
        e.odbiorca_idn,f.nip,f.nazwa,
        isnull(ltrim(rtrim(x.ulica)),'')+ISNULL(' '+ltrim(rtrim(x.nrdomu)),'')+ISNULL('m.'+ltrim(rtrim(x.nrmieszk)),'') ulica,
        isnull(ltrim(rtrim(x.kodpoczt)),'')+isnull(' '+ltrim(rtrim(x.miasto)),'') kod,kk.nazwa kraj 
    from doksprzed a 
    left join typ_dokumentu_sprzedazy d on a.typdoksp_id=d.typdoksp_id 
    left join odbiorca e on a.odbiorca_id=e.odbiorca_id
    inner join adrkontr x on e.adrwys_id=x.adrkontr_id 
    left join kraj kk on x.kraj_id=kk.kraj_id 
    inner join cechodb c on a.odbiorca_id=c.odbiorca_id 
    inner join katparam k on c.katparam_id=k.katparam_id 
    left join kontrahent f on e.kontrahent_id=f.kontrahent_id 
    left join stwystfakt i on a.stwystfakt_id=i.stwystfakt_id 
    where d.typdok_idn like 'FV_B%' and a.datdok between  %s and %s and left(i.stwystfakt_ids,3) like %s 
    and k.katparam_idn ='EFAKTURA' and c.wartoscparametru not like'TAK'
    group by a.odbiorca_id, i.stwystfakt_ids,i.nazwa,
        e.odbiorca_idn,f.nip,f.nazwa,isnull(ltrim(rtrim(x.ulica)),'')+ISNULL(' '+ltrim(rtrim(x.nrdomu)),'')+ISNULL('m.'+ltrim(rtrim(x.nrmieszk)),''),
        isnull(ltrim(rtrim(x.kodpoczt)),'')+isnull(' '+ltrim(rtrim(x.miasto)),''), kk.nazwa
    order by e.odbiorca_idn"""  # TODO: dopytać o order

SQL_SNR_ROZLICZENIA = """
    select count(r.id) as iledok, pl.id as odbiorca_id, l.hs->'mpk' as "Stanowisko_sprzedaży", l.nazwa as "Nazwa_stanowiska_sprzedaży",
        pl.hs->'umowa' as odbiorca_idn, pl.nip, pl.nazwa,
        (case when pl.hs->'ulica' is null or pl.hs->'ulica' = '' then pl.hs->'adres' else 
            pl.hs->'ulica'
        end) as ulica, 
        coalesce(pl.hs->'kodpocztowy', '') || ' ' || pl.miejscowosc as kod, '' as kraj
    from rozliczenia r 
    left join platnicy pl on pl.id=r.platnik 
    left join laboratoria l on l.symbol=r.laboratorium 
    where r.laboratorium=%s 
    and r.oddnia between %s and %s
    and r.dodnia between %s and %s
    and not r.del
    group by 2, 3, 4, 5, 6, 7, 8, 9, 10
"""

SQL_SNR_FAKTURY = """
    select count(r.id) as iledok, pl.id as odbiorca_id, l.hs->'mpk' as "Stanowisko_sprzedaży", l.nazwa as "Nazwa_stanowiska_sprzedaży",
        pl.hs->'umowa' as odbiorca_idn, pl.nip, pl.nazwa,
        (case when pl.hs->'ulica' is null or pl.hs->'ulica' = '' then pl.hs->'adres' else 
            pl.hs->'ulica'
        end) as ulica, 
        coalesce(pl.hs->'kodpocztowy', '') || ' ' || pl.miejscowosc as kod, '' as kraj
    from faktury f 
    left join rozliczenia r on r.faktura=f.id 
    left join platnicy pl on pl.id=r.platnik 
    left join laboratoria l on l.symbol=r.laboratorium 
    where f.laboratorium=%s 
    and f.datasprzedazy  between %s and %s
    and not f.del
    group by 2, 3, 4, 5, 6, 7, 8, 9, 10
"""

HTML_HEAD = """
<html>
<head>
    <style type="text/css">
        @page {
          size: A4;
          padding: 0;
          margin: 0;
          margin-top: 17pt;
        }
        @media print {
          html, body {
            width: 210mm;
            height: 297mm;
            margin: 0;
            padding: 0;
            font-family: 'Arial', 'Helvetica', sans-serif;
            font-size: 9pt;
          }
        }
        div#naklejki {
            margin-left: 5mm;
        }
        div.naklejka {
            width: 67mm;
            height: 35mm;
            float: left;
            border: 1pt dashed #fff;
            border-collapse: collapse;
            box-sizing: border-box;
            -moz-box-sizing: border-box;
            -webkit-box-sizing: border-box;
            position: relative;
            padding: 3mm;
        }
        div.naklejkastopka {
            position: absolute;
            bottom: 0;
            width: 60mm;
            height: 7mm;
            font-size: 7pt;
        }
        span.nrk {
            float: left;
            padding 3mm: 
        }
        span.nrf {
            float: right;
            padding 3mm: 
        }
    </style>

</head>
<body>
<div id="naklejki">
"""

HTML_FOOTER = """
    </div>
</body>
</html>
"""


def naklejka(row):
    res = '<div class="naklejka">'
    res += '%s<br />%s<br />%s' % (row['nazwa'], row['ulica'], row['kod'])
    if row['kraj'] is not None and len(row['kraj'].strip()) > 2 and row['kraj'].strip().lower() != 'polska':
        res += '<br />' + row['kraj']
    res += '<div class="naklejkastopka"><span class="nrk">%s</span><span class="nrf">%s</span></div>' % (
        row['odbiorca_idn'], ('%d faktur' % row['iledok'] if row['iledok'] > 1 else '')
    )
    res += '</div>'
    return res


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 31)
    if params['src'] == 'simple':
        if params['stanowisko'] is None or len(params['stanowisko'].strip()) < 2:
            raise ValidationError("Podaj stanowisko sprzedaży")
    elif params['src'] in ('snrf', 'snrr'):
        if params['lab'] is None or len(params['lab'].strip()) < 2:
            raise ValidationError("Podaj symbol laboratorium")
    else:
        raise ValidationError(f"Nieznane źródło faktur {params['src']}")
    print_task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'report_print',
    }
    report.create_task(print_task)
    report.save()
    return report


def report_print(task_params):
    res = []
    params = task_params['params']
    xlsx_cols = 'nazwa,ulica,kod,kraj,odbiorca_idn,Stanowisko_sprzedaży,iledok'.split(',')
    xlsx_col_titles = 'Nazwa,Ulica,Kod,Kraj,Nr klienta,MPK,Ile dokumentów'.split(',')
    xlsx_rows = []
    out_fn = random_path(extension='pdf')
    if params['src'] == 'simple':
        podnazwa = params['stanowisko']
        stanowisko = params['stanowisko'].strip() + '%'
        sd = SimpleDatasource()
        rows = sd.dict_select(SQL_SIMPLE, [params['dataod'], params['datado'], stanowisko])
    elif params['src'] in ('snrf', 'snrr'):
        podnazwa = params['lab']
        snr = SNR()
        if params['src'] == 'snrf':
            rows = snr.dict_select(SQL_SNR_FAKTURY, [params['lab'], params['dataod'], params['datado']])
        else:
            rows = snr.dict_select(SQL_SNR_ROZLICZENIA, [params['lab'], params['dataod'], params['datado'], params['dataod'], params['datado']])
    else:
        raise RuntimeError(params['src'])
    pdf_fn = 'naklejki_%s_%s-%s.pdf' % (slugify(podnazwa), params['dataod'], params['datado'])
    xlsx_fn = 'lista_%s_%s-%s.xlsx' % (slugify(podnazwa), params['dataod'], params['datado'])
    html = HTML_HEAD
    for row in rows:
        html += naklejka(row)
        xlsx_rows.append([row[c] for c in xlsx_cols])
    html += HTML_FOOTER
    pdf = HTML(string=html)
    pdf.write_pdf(out_fn)
    with open(out_fn, 'rb') as f:
        out_content = f.read()
    os.unlink(out_fn)
    res.append({
        "type": "download",
        "content": base64.b64encode(out_content).decode(),
        "content_type": "application/pdf",
        "filename": pdf_fn,
    })
    rep = ReportXlsx({'results': [
        {
            'type': 'table',
            'header': xlsx_col_titles,
            'data': prepare_for_json(xlsx_rows),
            'params': prepare_for_json(params)
        }]})
    res.append({
        'type': 'download',
        'content': base64.b64encode(rep.render_as_bytes()).decode(),
        'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'filename': xlsx_fn,
    })
    return res
