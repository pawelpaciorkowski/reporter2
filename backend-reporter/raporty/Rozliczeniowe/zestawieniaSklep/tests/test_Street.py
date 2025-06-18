from raporty.Rozliczeniowe.zestawieniaSklep.utils.Street import Street


def test_full_name():
    street = Street(street_type='ul.', street_name='Stępińska')
    assert street.full_street == 'ul. Stępińska'
