from .postgres import PostgresDatasource


class SNR(PostgresDatasource):
    def __init__(self):
        PostgresDatasource.__init__(self, "dbname='rozliczeniowa' user='postgres' host='2.0.4.101' port=5432")

    def laboratoria(self):
        return self.select("select * from laboratoria")

    def struktura(self):
        res = {
            "regiony": self.select("select * from regiony"),
            "laboratoria": self.select("select * from laboratoria"),
            "platnicy": self.select("select * from platnicy"),
            "platnicywlaboratoriach": self.select("select * from platnicywlaboratoriach"),
            "zleceniodawcy": self.select("select * from zleceniodawcy"),
        }
        for k in res:
            res[k] = self.remove_columns(res[k], "tsidx")
        return res

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class SNRTest(SNR):
    def __init__(self):
        PostgresDatasource.__init__(self, "dbname='rozliczeniowa' user='postgres' host='10.1.1.98' port=5432")


"""

(Column(name='id', type_code=1043, display_size=None, internal_size=-1, precision=None, scale=None, null_ok=None),
 Column(name='mid', type_code=1043, display_size=None, internal_size=-1, precision=None, scale=None, null_ok=None),
 Column(name='del', type_code=16, display_size=None, internal_size=1, precision=None, scale=None, null_ok=None),
 Column(name='st', type_code=23, display_size=None, internal_size=4, precision=None, scale=None, null_ok=None),
 Column(name='dc', type_code=1114, display_size=None, internal_size=8, precision=None, scale=None, null_ok=None),
 Column(name='pc', type_code=1043, display_size=None, internal_size=-1, precision=None, scale=None, null_ok=None),
 Column(name='cmt', type_code=25, display_size=None, internal_size=-1, precision=None, scale=None, null_ok=None),
 Column(name='symbol', type_code=1043, display_size=None, internal_size=-1, precision=None, scale=None, null_ok=None),
 Column(name='nazwa', type_code=1043, display_size=None, internal_size=-1, precision=None, scale=None, null_ok=None),
 Column(name='vpn', type_code=1043, display_size=None, internal_size=-1, precision=None, scale=None, null_ok=None),
 Column(name='bazacentrum', type_code=1043, display_size=None, internal_size=-1, precision=None, scale=None, null_ok=None),
 Column(name='hs', type_code=16386, display_size=None, internal_size=-1, precision=None, scale=None, null_ok=None),
 Column(name='opiekun', type_code=1043, display_size=None, internal_size=-1, precision=None, scale=None, null_ok=None),
 Column(name='platnik', type_code=1043, display_size=None, internal_size=-1, precision=None, scale=None, null_ok=None),
 Column(name='aktywne', type_code=16, display_size=None, internal_size=1, precision=None, scale=None, null_ok=None))

"""
