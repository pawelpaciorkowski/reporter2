from datasources.postgres import PostgresDatasource


class BankKrwiDatasource(PostgresDatasource):
    def __init__(self, system, adres, baza):
        self._system = system
        self._odmiany = None
        dsn = "dbname='%s' user='bank_raporty' password='bank_raporty' host='%s' port=5432" % (baza, adres)
        PostgresDatasource.__init__(self, dsn)

    def odmiany_skladnikow(self):
        if self._odmiany is None:
            self._odmiany = {}
            # tylkojednostka - nie ma w starszych bankach
            for row in self.dict_select("""select id, symbol, nazwa, kolejnosc, krzyzowany, magrupe, marh
                    from rodzajematerialow where not del and not hst
                """):
                self._odmiany[row['id']] = row
                self._odmiany[row['id']]['odmiany'] = {}
            for row in self.dict_select("""select rodzaj, symbol, nazwa, bit, przed 
                    from odmianymaterialow where not del and not hst 
                """):
                if row['rodzaj'] not in self._odmiany:
                    continue
                self._odmiany[row['rodzaj']]['odmiany'][row['bit']] = row
        return self._odmiany

    def dane_rodzaju_odmiany(self, rodzaj, odmiana):
        odmiany = self.odmiany_skladnikow()
        res_rodz = odmiany[rodzaj]
        res_odm = []
        if odmiana is not None:
            for bit in range(64):
                if odmiana & (1<<bit) and bit in res_rodz['odmiany']:
                    res_odm.append(res_rodz['odmiany'][bit])
        return res_rodz, res_odm

    def odmiana_symbol(self, rodzaj, odmiana):
        rodz, odmiany = self.dane_rodzaju_odmiany(rodzaj, odmiana)
        res = rodz['symbol']
        for odm in odmiany:
            if odm['przed']:
                res = odm['symbol'] + res
            else:
                res = res + odm['symbol']
        return res


    def odmiana_nazwa(self, rodzaj, odmiana):
        rodz, odmiany = self.dane_rodzaju_odmiany(rodzaj, odmiana)
        res = rodz['nazwa']
        for odm in odmiany:
            if odm['przed']:
                res = odm['nazwa'] + ' ' + res
            else:
                res = res + ' ' + odm['nazwa']
        return res
