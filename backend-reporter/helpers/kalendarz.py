import datetime
import re


class KalendarzException(Exception):
    pass


class Kalendarz():
    def __init__(self):
        self.ustaw_teraz()
        self.ost_pocz_kon = None
        self.polski = False

    def dzien_roboczy(self, czas):
        if isinstance(czas, str):
            czas = self.parsuj_czas(czas)
        if czas.weekday() in (5, 6):
            return False
        if (czas.month, czas.day) in ((1, 1), (1, 6), (5, 1), (5, 3), (8, 15), (11, 1), (11, 11), (12, 25), (12, 26)):
            return False
        else:
            a = czas.year % 19
            b = czas.year % 4
            c = czas.year % 7
            d = (a * 19 + 24) % 30
            e = (2 * b + 4 * c + 6 * d + 5) % 7
            if d == 29 and e == 6:
                d -= 7
            if d == 28 and e == 6 and a > 10:
                d -= 7
            wielkanoc_niedziela = czas.replace(month=3, day=22) + datetime.timedelta(days=d + e)
            wielkanoc_poniedzialek = wielkanoc_niedziela + datetime.timedelta(days=1)
            boze_cialo = wielkanoc_niedziela + datetime.timedelta(days=60)
            if (czas.month, czas.day) in (
                    (wielkanoc_niedziela.month, wielkanoc_niedziela.day),
                    (wielkanoc_poniedzialek.month, wielkanoc_poniedzialek.day),
                    (boze_cialo.month, boze_cialo.day),
            ):
                return False
        return True

    def rok_przestepny(self, rok):
        if rok % 4 == 0:
            if rok % 100 == 0:
                if rok % 400 == 0:
                    return True
                else:
                    return False
            else:
                return True
        else:
            return False

    def ostatni_dzien_miesiaca(self, rok, miesiac):
        if miesiac == 2:
            return 29 if self.rok_przestepny(rok) else 28
        elif miesiac in (4, 6, 9, 11):
            return 30
        else:
            return 31

    def parsuj_czas(self, czas, throw_exception=False, uwzgledniaj_teraz=True):
        res = None
        odniesienie = self.teraz if uwzgledniaj_teraz else datetime.datetime.now()
        if czas in (None, 't', 'T'):
            res = odniesienie
        elif isinstance(czas, int):
            pass
        elif isinstance(czas, str):
            czas = czas.strip().upper()
            if czas.startswith('W'):
                return self.parsuj_czas('-1D ' + czas[1:], throw_exception, uwzgledniaj_teraz)
            if czas.startswith('J'):
                return self.parsuj_czas('+1D ' + czas[1:], throw_exception, uwzgledniaj_teraz)
            if czas.startswith('-') or czas.startswith('+'):
                res = odniesienie
                kierunek = -1 if czas.startswith('-') else 1
                tylko_robocze = False
                liczby = re.findall(r'\d+', czas)
                licznik = 0
                delta = None
                if len(liczby) == 1:
                    licznik = int(liczby[0])
                if czas.endswith('G'):
                    delta = datetime.timedelta(hours=kierunek)
                elif czas.endswith('D'):
                    delta = datetime.timedelta(days=kierunek)
                elif czas.endswith('DR'):
                    delta = datetime.timedelta(days=kierunek)
                    tylko_robocze = True
                elif czas.endswith('T'):
                    delta = datetime.timedelta(days=7 * kierunek)
                if delta is not None:
                    while licznik > 0:
                        res = res + delta
                        if not tylko_robocze or self.dzien_roboczy(res):
                            licznik -= 1
                else:
                    if czas.endswith('M'):
                        pass
                    elif czas.endswith('R') or czas.endswith('L'):
                        licznik *= 12
                    elif throw_exception:
                        raise KalendarzException('Nieznany format odstępu czasowego', czas)
                    for _ in range(licznik):
                        rok = res.year
                        mies = res.month + kierunek
                        dzien = res.day
                        if mies == 0:
                            rok -= 1
                            mies = 12
                        elif mies == 13:
                            rok += 1
                            mies = 1
                        try:
                            res = res.replace(year=rok, month=mies, day=dzien)
                            while res.day < odniesienie.day:
                                try:
                                    res = res.replace(day=res.day + 1)
                                except:
                                    break
                        except ValueError:
                            res = res.replace(year=rok, month=mies, day=self.ostatni_dzien_miesiaca(rok, mies))
            elif czas.startswith('P') or czas.startswith('K'):
                self.ost_pocz_kon = czas[0]
                if czas.endswith('M'):
                    r = odniesienie.year
                    m = odniesienie.month
                    d = odniesienie.day
                    g, i, s = 0, 0, 0
                    if czas.endswith('ZM'):
                        m -= 1
                        if m == 0:
                            r -= 1
                            m = 12
                    elif czas.endswith('M'):
                        pass
                    if self.ost_pocz_kon == 'P':
                        d = 1
                    elif self.ost_pocz_kon == 'K':
                        d = self.ostatni_dzien_miesiaca(r, m)
                        g, i, s = 23, 59, 59
                elif czas.endswith('T'):
                    if 'Z' in czas:
                        odniesienie -= datetime.timedelta(days=7)
                    if self.ost_pocz_kon == 'P':
                        while odniesienie.weekday() != 0:
                            odniesienie -= datetime.timedelta(days=1)
                        g, i, s = 0, 0, 0
                    else:
                        while odniesienie.weekday() != 6:
                            odniesienie += datetime.timedelta(days=1)
                        g, i, s = 23, 59, 59

                    r = odniesienie.year
                    m = odniesienie.month
                    d = odniesienie.day

                res = odniesienie.replace(year=r, month=m, day=d, hour=g, minute=i, second=s)
            else:
                czas = czas.replace('T', ' ')
                if ' ' not in czas:
                    czas = czas + ' 0:00:00'
                data_godz = czas.split(' ')
                try:
                    data = [int(x) for x in data_godz[0].split('-')]
                    if len(data) == 1:
                        data = [odniesienie.month] + data
                    if len(data) == 2:
                        data = [odniesienie.year] + data
                    if data[0] < 100:
                        data[0] += 2000
                    res = odniesienie.replace(year=data[0], month=data[1], day=data[2])
                    godz = [int(x) for x in data_godz[1].split(':')]
                    while len(godz) < 3:
                        godz.append(0)
                    res = res.replace(hour=godz[0], minute=godz[1], second=godz[2])
                except:
                    pass
                # poparsować normalnie
        elif isinstance(czas, datetime.date):
            res = czas
        elif isinstance(czas, datetime.datetime):
            res = czas
        elif throw_exception:
            raise KalendarzException('Nieznany typ danych', czas.__class__)
        if res is None and throw_exception:
            raise KalendarzException('Nie udało się odczytać czasu', czas)
        return res

    def ustaw_teraz(self, czas=None):
        self.teraz = self.parsuj_czas(czas, throw_exception=True, uwzgledniaj_teraz=False)

    def data(self, czas=None, throw_exception=False):
        if czas is None:
            czas = self.teraz
        res = self.parsuj_czas(czas, throw_exception=throw_exception)
        if res is not None:
            if self.polski:
                return res.strftime('%d-%m-%Y')
            else:
                return res.strftime('%Y-%m-%d')

    def data_godz(self, czas=None, throw_exception=False):
        if czas is None:
            czas = self.teraz
        if isinstance(czas, str) and ' ' not in czas and ':' in czas:
            czas = self.data() + ' ' + czas.strip()
        try:
            res = self.parsuj_czas(czas, throw_exception=True)
        except KalendarzException as e:
            if ' ' in czas:
                czas_t = czas.split(' ', 1)
                res = self.parsuj_czas(czas_t[0], throw_exception=throw_exception)
                if res is not None:
                    godz = czas_t[1].split(':')
                    try:
                        res = res.replace(hour=int(godz[0]))
                        if len(godz) > 1:
                            res = res.replace(minute=int(godz[1]))
                        else:
                            res = res.replace(minute=0)
                    except Exception as e:
                        if throw_exception:
                            raise KalendarzException('Nieznany format godziny')
            elif throw_exception:
                raise e
            else:
                res = None
        if res is not None:
            return self.data(res) + ' ' + res.strftime('%H:%M')

    def policz_dni(self, data_od, data_do):
        data_od = self.parsuj_czas(data_od).date()
        data_do = self.parsuj_czas(data_do).date()
        return (data_do - data_od).days

    def dni(self, data_od=None, data_do=None):
        last_teraz = self.teraz
        if data_od is None:
            data_od = self.data('T')
        if data_do is None:
            data_do = self.data('T')
        if data_od > data_do:
            data_od, data_do = data_do, data_od
        cnt = 0
        self.ustaw_teraz(data_od)
        while True:
            data = self.data('T')
            yield data
            if data == data_do:
                break
            if cnt >= 5000:
                raise RuntimeError("Za dużo dni")
            cnt += 1
            self.ustaw_teraz(self.data("+1D"))
        self.teraz = last_teraz

    def policz_dni_robocze(self, data_od, data_do):
        odwroc = False
        licznik = 0
        data_od = self.parsuj_czas(data_od).date()
        data_do = self.parsuj_czas(data_do).date()
        if data_do < data_od:
            odwroc = True
            data_od, data_do = data_do, data_od
        while data_od != data_do:
            if self.dzien_roboczy(data_od):
                licznik += 1
            data_od += datetime.timedelta(days=1)
        if odwroc:
            licznik = -licznik
        return licznik

    def zakres_dat(self, data_od, data_do):
        res = []
        data_od = self.parsuj_czas(data_od).date()
        data_do = self.parsuj_czas(data_do).date()
        if (data_do - data_od).days >= 0:
            data = data_od
            while data <= data_do:
                res.append(self.data(data))
                data = data + datetime.timedelta(days=1)
        return res
