import json
import os
import traceback
import time
import progressbar
import datetime

import datasources.centrum
from datasources.nocka import NockaDatasource
from datasources.reporter import ReporterDatasource
from tasks import TaskGroup, Task
from helpers import Kalendarz, get_snr_connection, get_centrum_connection, divide_chunks, divide_by_key, \
    globalny_hash_pacjenta
from helpers.cli import pb_iterate

MENU_ENTRY = None

SQL_LAB = """
    select w.id, 
        trim(bad.symbol) as bad_symbol, bad.nazwa as bad_nazwa,
        trim(mat.symbol) as material,
        trim(pr.symbol) as pr_symbol, pr.nazwa as pr_nazwa, 
        trim(ap.symbol) as ap_symbol, ap.nazwa as ap_nazwa,
		trim(st.symbol) as st_symbol, st.nazwa as st_nazwa,
        w.kodkreskowy, zl.kodkreskowy as zl_kodkreskowy,
        zl.numer, zl.datarejestracji,
        trim(o.symbol) as zl_symbol, o.nazwa as zl_nazwa,
        trim(pl.symbol) as pl_symbol, pl.nazwa as pl_nazwa,
        w.dystrybucja, w.wyslanezlecenie, bad.czasmaksymalny
    from listyrobocze lr
    left join pracownie pr on pr.id=lr.pracownia
    left join aparaty ap on ap.id=lr.aparat
	left join stanowiska st on st.id=lr.stanowisko
    left join wykonania w on w.listarobocza=lr.id
    left join badania bad on bad.id=w.badanie
    left join materialy mat on mat.id=w.material
    left join zlecenia zl on zl.id=w.zlecenie
    left join oddzialy o on o.id=zl.oddzial
    left join platnicy pl on pl.id=zl.platnik
    where w.id is not null
    order by w.dystrybucja
"""


class LabSynchroniser:
    def __init__(self, lab):
        self.lab = lab
        self.ds = NockaDatasource(read_write=True)

    def synchronizuj(self):
        to_insert = []
        with get_centrum_connection(self.lab, fresh=True) as conn:
            for row in conn.raport_slownikowy(SQL_LAB, sql_pg=SQL_LAB):
                row['lab'] = self.lab
                to_insert.append(row)
        self.ds.execute("delete from listyrobocze where lab=%s", [self.lab])
        self.ds.multi_insert('listyrobocze', to_insert)
        self.ds.commit()


def lab_sync_task(task_params):
    lab = task_params['target']
    ls = LabSynchroniser(lab)
    ls.synchronizuj()


def synchronizuj_listy_robocze():
    rep = ReporterDatasource()
    tasks = []
    for lab in rep.dict_select("select * from laboratoria where aktywne and adres_fresh is not null and wewnetrzne"):
        tasks.append({
            'type': 'centrum',
            'priority': 1,
            'target': lab['symbol'],
            'params': {},
            'function': 'lab_sync_task',
        })
    task_group = TaskGroup(__PLUGIN__, {})
    for task in tasks:
        task_group.create_task(task)
    task_group.save()
    finished = False
    finished_labs = []
    success_labs = []
    failed_labs = []
    pb = progressbar.ProgressBar(maxval=len(tasks))
    pb.start()
    while not finished:
        for job_id, params, status, result in task_group.get_tasks_results():
            lab = params['target']
            if lab not in finished_labs:
                if status == 'finished':
                    finished_labs.append(lab)
                    success_labs.append(lab)
                elif status == 'failed':  # timeout to też failed
                    finished_labs.append(lab)
                    failed_labs.append(lab)
        pb.update(len(finished_labs))
        if len(finished_labs) == len(tasks):
            finished = True
        else:
            time.sleep(5)
    pb.finish()
    print('  pobrano dane z %d labów, nie udało się pobrać z %d: %s' % (
        len(success_labs), len(failed_labs), ', '.join(failed_labs)
    ))
