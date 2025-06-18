from datasources.hl7ctl import HL7Ctl
from datasources.snrkonf import SNRKonf
from helpers import prepare_for_json


'''


    db = HL7Ctl()
    conn_count = 0
    cols, rows = db.select("""select * from zlaczki zl where zl.klient=%s""", [params['klient']])


'''

class ZlaczkiKlienta:
    def __init__(self, klient, labs):
        self.klient = klient
        self.labs = labs

    def html(self):
        db = HL7Ctl()
        conn_count = 0
        rows = db.dict_select("""select zl.*, l.symbol as laboratorium,
            st.error, st.warning, st.ts
            from zlaczki zl 
            left join laboratoria l on l.id=zl.lab
            left join status st on st.zlaczka=zl.id
            where zl.klient=%s
        order by st.ts desc limit 1
        """, [self.klient])
        if len(rows) == 0:
            return None
        data = []
        for row in rows:
            status = []
            status_color = '#ffffff'
            if row['error']:
                status.append("NIE DZIAŁA (%s)" % row['ts'])
                status_color = '#ff0000'
            elif row['warning']:
                status.append("OSTRZEŻENIE (%s)" % row['ts'])
                status_color = '#ffff00'
            else:
                status.append("OK (%s)" % row['ts'])
                status_color = '#00ff00'
            uwagi = []
            # uwagi.append(repr(row))
            if row['testowa']:
                uwagi.append('złączka testowa')
            if not row['aktywna']:
                uwagi.append('złączka nieaktywna')
            status_cell = {
                'value': '; '.join(status),
                'background': status_color
            }
            wiersz = [row['laboratorium'], row['nazwa'], status_cell, ', '.join(uwagi)]
            data.append(wiersz)

        return {
            'type': 'table',
            'title': 'Złączki HL7',
            'header': 'Laboratorium,Nazwa,Status,Uwagi'.split(','),
            'data': prepare_for_json(data)
        }

class ZlaczkiLabu:
    def __init__(self, lab):
        self.lab = lab

    def html(self):
        db = HL7Ctl()
        snr = SNRKonf()
        conn_count = 0
        rows = db.dict_select("""select zl.*, l.symbol as laboratorium,
            st.error, st.warning, st.ts,
            case zlll.lab is not null when true then 2 else
                case zll.lab is not null when true then 1 else 0 end 
            end as indent
            from zlaczki zl 
            left join laboratoria l on l.id=zl.lab
            left join zlaczki zll on zll.id=zl.parent
            left join laboratoria ll on ll.id=zll.lab
            left join zlaczki zlll on zlll.id=zll.parent
            left join laboratoria lll on lll.id=zlll.lab
            left join status st on st.zlaczka=zl.id
            where (l.symbol=%s or ll.symbol=%s or lll.symbol=%s)
            and st.aktualny
            order by coalesce(zlll.nazwa, '') || coalesce(zll.nazwa, '') || coalesce(zl.nazwa, '') 
        """, [self.lab, self.lab, self.lab])
        if len(rows) == 0:
            return None
        data = []
        id_klientow = []
        klienci = {}
        for row in rows:
            if row['klient'] is not None and row['klient'] not in id_klientow:
                id_klientow.append(row['klient'])
        for ident in id_klientow:
            for row in snr.dict_select("select nazwa from platnicy where id=%s", [ident]):
                klienci[ident] = row['nazwa']
        for row in rows:
            status = []
            status_color = '#ffffff'
            if row['error']:
                status.append("NIE DZIAŁA (%s)" % row['ts'])
                status_color = '#ff0000'
            elif row['warning']:
                status.append("OSTRZEŻENIE (%s)" % row['ts'])
                status_color = '#ffff00'
            else:
                status.append("OK (%s)" % row['ts'])
                status_color = '#00ff00'
            uwagi = []
            # uwagi.append(repr(row))
            if row['testowa']:
                uwagi.append('złączka testowa')
            if not row['aktywna']:
                uwagi.append('złączka nieaktywna')
            status_cell = {
                'value': '; '.join(status),
                'background': status_color
            }
            klient = None
            if row['klient'] in klienci:
                klient = klienci[row['klient']]
            wiersz = [klient, " -- " * row['indent'] + row['nazwa'], status_cell, ', '.join(uwagi)]
            data.append(wiersz)

        return {
            'type': 'table',
            'title': 'Złączki HL7',
            'header': 'Klient,Nazwa,Status,Uwagi'.split(','),
            'data': prepare_for_json(data)
        }
