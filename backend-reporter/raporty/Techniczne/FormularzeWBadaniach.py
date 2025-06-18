import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, empty
from datasources.snrkonf import SNRKonf

MENU_ENTRY = 'Formularze w badaniach'

REQUIRE_ROLE = ['C-CS']

ADD_TO_ROLE = ['R-MDO', 'L-PRAC']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pracownie_domyslne=True),
    TextInput(field='pracownia', title='Pracownia (symbol)'),
))

SQL = """
    select a.pracownia, a.badanie, a.material, list(a.formularz) as formularze
    from
    (select 
        p.symbol as pracownia,
        b.Symbol as BADANIE, 
        mat.Symbol as MATERIAL,
        case when bwf.id is not null then
            trim(coalesce(f.symbol, '---')) || ' (' || trim(coalesce(gwf.symbol, '')) || ')'
        else '' end as formularz
    FROM PowiazaniaMetod pm 
    left outer join Metody m on m.id = pm.metoda and m.del = 0 
    left outer join Pracownie p on p.id = m.pracownia and p.del = 0 
    left outer join Badania b on b.id = pm.badanie and b.del = 0 
    left outer join Systemy s on s.id = pm.system and s.del = 0 
    left join materialywbadaniach mwb on mwb.badanie=b.id and mwb.del=0
    left join materialy mat on mat.id=mwb.material and mat.del=0
    left join badaniawformularzach bwf on bwf.badanie=b.id and bwf.material=mat.id and bwf.del=0
    left join formularze f on f.id=bwf.formularz and f.del=0
    left join grupywformularzach gwf on gwf.id=bwf.grupa and gwf.del=0
    WHERE 
        m.DEL = 0 and b.DEL = 0 and s.DEL = 0 and p.del =0 and pm.DEL =0 and p.symbol=?
        and pm.dowolnytypzlecenia=1 and pm.dowolnarejestracja=1 and pm.dowolnyoddzial=1 and pm.dowolnyplatnik=1 and pm.dowolnymaterial=1
    ORDER BY 1,2,3,bwf.kolejnosc) as a
    group by 1, 2, 3"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    params['pracownia'] = (params['pracownia'] or '').upper().strip()
    if not empty(params['pracownia']):
        snr = SNRKonf()
        rows = snr.dict_select("select * from pozycjekatalogow where katalog='PRACOWNIE' and symbol=%s and not del",
                               [params['pracownia']])
        if len(rows) == 0:
            raise ValidationError("Nie ma takiej pracowni")
        params['pracownia_nazwa'] = rows[0]['nazwa']
    else:
        params['pracownia'] = None
        params['pracownia_nazwa'] = None
    lab_task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lab',
    }
    report.create_task(lab_task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    sql = SQL
    if params['pracownia'] is not None:
        sql_params = [params['pracownia']]
    else:
        sql_params = []
        sql = sql.replace('and p.symbol=?', '')
    with get_centrum_connection(task_params['target']) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
    return {
        'type': 'table',
        'title': params['pracownia_nazwa'] or 'Wszystkie pracownie',
        'header': 'Pracownia,Badanie,Materiał,Formularze (sekcje)'.split(','),
        'data': prepare_for_json(rows)
    }
