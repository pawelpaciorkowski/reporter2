import copy
import re
import os
import shutil
import base64
import datetime
import time

# TODO: przy sprawdzaniu czy były kody sprawdzać też kody wykonań a nie tylko zleceń
# przykład LUBLINC listopad 2022 kod 5863358210

from datasources.reporter import ReporterDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from helpers.crystal_ball.marcel_servers import katalog_wydrukow
from helpers.validators import validate_date_range, validate_symbol
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, divide_chunks, random_path, \
    copy_from_remote, ZIP, simple_password, empty

MENU_ENTRY = 'Data Transfer badania kliniczne'

REQUIRE_ROLE = ['C-CS']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Eksport wyników na zleceniodawcę wg dat zatwierdzenia. Format ustalony przez Paulinę Berezę."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    TextInput(field='oddzial', title='Zleceniodawca (symbol)'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))

SQL = """
   select 
   	pac.numer as "PatientID",
   	coalesce(w.kodkreskowy, z.kodkreskowy) as "SpecimenID",
   	w.godzina as "DateTimeOfSpecimenCollection",
   	z.zewnetrznyidentyfikator as "VisitNumber",
   	'' as "VisitName",
   	(case when b.nazwaalternatywna is not null and b.nazwaalternatywna != '' then
   		case when par.nazwaalternatywna is not null and par.nazwaalternatywna != '' then
   			case when par.nazwaalternatywna = b.nazwaalternatywna then
   				b.nazwaalternatywna else b.nazwaalternatywna || ' - ' || par.nazwaalternatywna end
   		else case when par.nazwa = b.nazwaalternatywna then
   				b.nazwaalternatywna else b.nazwaalternatywna || ' - ' || par.nazwa end
   			end
	else
		case when par.nazwa=b.nazwa then b.nazwa else b.nazwa || ' - ' || par.nazwa end
   	end) as "LabTestOrExaminationName",
   	gb.nazwa as "CategoryForLabTest",
   	case when w.bladwykonania is null then 
   	  case when par.typ=1 or par.typ=3 
        then cast(cast(y.wynikliczbowy as numeric(20,3)) as varchar)
        else y.wyniktekstowy end
   	else bw.nazwa end as "ResultOrFindingInOriginalUnits",
   	substring(par.format, strpos(par.format, ' ')+1) as "OriginalUnits",
   	n.zakresod as "ReferenceRangeLowerLimitInOrig",
   	n.zakresdo as "ReferenceRangeUpperLimitInOrigUnit",
   	coalesce(m.nazwaalternatywna, m.nazwa) as "SpecimenType"
   from zlecenia z   
   left join wykonania w on w.zlecenie=z.id
   left join badania b on b.id=w.badanie
   left join grupybadan gb on gb.id=b.grupa
   left join materialy m on m.id=w.material
   left join pacjenci pac on pac.id=z.pacjent
   left join wyniki y on y.wykonanie=w.id and y.ukryty=0
   left join parametry par on par.id=y.parametr
   left join bledywykonania bw on bw.id=w.bladwykonania
   left join normy n on n.id=y.norma
   where z.oddzial in (select id from oddzialy where symbol=?) and w.zatwierdzone between ? and ?
   order by z.datarejestracji, z.numer, b.kolejnosc, par.kolejnosc 
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 2 * 365)
    lb_task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': {
            'dataod': params['dataod'],
            'datado': params['datado'],
            'oddzial': params['oddzial'],
        },
        'function': 'raport_lab',
    }
    report.create_task(lb_task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(SQL, [params['oddzial'], params['dataod'], params['datado']])
        return {
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(rows)
        }
