from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_bank_krwi_connection

MENU_ENTRY = 'Wydania skł/płeć/wiek'

LAUNCH_DIALOG = Dialog(title='Wydania składników w podziale na płeć i wiek', panel=VBox(
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', bank_krwi=True),
    DateInput(field='dataod', title='Data od', default='PZM'),
    DateInput(field='datado', title='Data do', default='KZM'),
    Switch(field='odmiany', title='Podział na odmiany składników')
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    validate_date_range(params['dataod'], params['datado'], 366)

    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_bank'
    }
    report.create_task(task)
    report.save()
    return report


def raport_bank(task_params):
    params = task_params['params']
    bank = get_bank_krwi_connection(task_params['target'])
    header = 'Symbol,Nazwa,Płeć,Wiek,Ile wydań,Ile worków,Ilu pacjentów,Ile jednostek'.split(',')
    rows = []
    sql = """
         select m.rodzaj, m.odmiana, rm.kolejnosc,
            pac.plec, 
            case 
                when date_part('year', age(d.data, pac.dataurodzenia)) < 5 then 'pon. 5'
                when date_part('year', age(d.data, pac.dataurodzenia)) < 15 then '5-14'
                when date_part('year', age(d.data, pac.dataurodzenia)) < 45 then '15-44' 
                when date_part('year', age(d.data, pac.dataurodzenia)) < 60 then '45-59' 
                else 'pow. 60'
            end as wiek,
            count(t.id) as ile_s,
            count(distinct d.id) as ile_w,
            count(distinct d.pacjent) as ile_p,
            sum(m.iloscj) as ile_j
         from trescdokumentow t
          left join Dokumenty D on D.ID = T.Dokument
          LEFT JOIN materialy m ON m.id = t.material
          LEFT JOIN rodzajematerialow rm ON rm.id = m.rodzaj
          LEFT JOIN kontrahenci k ON k.id = d.kontrahent
          LEFT JOIN GrupyKontrahentow as GK on GK.ID = K.Grupa
          left join pacjenci pac on pac.id=d.pacjent
          where D.Kategoria = 1
            and D.data >= %s
            AND D.data <= %s
            and not d.DEL and not d.HST and not t.DEL and not t.HST
            and D.Pacjent is not null 
        group by 1, 2, 3, 4, 5
        order by rm.kolejnosc
    """
    if not params['odmiany']:
        sql = sql.replace('m.odmiana', 'null as odmiana')
    for row in bank.dict_select(sql, [params['dataod'], params['datado']]):
        res_row = [
            bank.odmiana_symbol(row['rodzaj'], row['odmiana']),
            bank.odmiana_nazwa(row['rodzaj'], row['odmiana']),
            row['plec'], row['wiek'],
            row['ile_w'], row['ile_s'], row['ile_p'], row['ile_j']
        ]
        rows.append(res_row)

    return {
        'type': 'table',
        'header': header,
        'data': prepare_for_json(rows)
    }


"""
bazka bank:
zamowienia: pacjent, rodzajmaterialu, odmianamaterialu, grupa, rh, fenotyp, ilosc, jednostka, 
dokumenty: rodzaj, kategoria, data, pacjent, godzinawydania, godzinadostarczenia, zamowienie
trescdokumentow: del, dokument, material
pacjenci: plec, dataurodzenia
materialy: rodzaj, odmiana, grupa, rh, fenotyp, numer

zestawienie: ilość wydań, ilość jednostek, ilość różnych pacjentów

"""
