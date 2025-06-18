from raporty.Rozliczeniowe.zestawieniaSklep.utils.CollectionPoint import CollectionPoint, CollectionPointMiesieczny
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Street import Street


class TestCollectionPoint:

    street = Street(street_type='ul.', street_name='Stępińska')

    def test_dict_representation(self):

        cp = CollectionPoint(street=self.street, city='Warszawa', mpk='002001', symbol='COAMB')

        data = {'mpk': '002001', 'symbol': 'COAMB', 'street': self.street, 'city': 'Warszawa'}
        assert data == cp.dict()

    def test_report_reporesentation_miesieczny(self):

        cp = CollectionPointMiesieczny(street=self.street, city='Warszawa', mpk='002001',
                             symbol='COAMB')

        assert cp.report_representation() == 'ul. Stępińska, Warszawa, Symbol punktu: COAMB'
