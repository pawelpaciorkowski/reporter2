from .postgres import PostgresDatasource


class HL7Ctl(PostgresDatasource):
    def __init__(self):
        PostgresDatasource.__init__(self, "dbname='hl7ctl' user='hl7ctl' password='hl7ctl' host='2.0.206.213' port=5432")
