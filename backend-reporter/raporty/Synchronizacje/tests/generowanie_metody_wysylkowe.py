import os
from raporty.Synchronizacje.generowanie_metod_wysylkowych import GenerowanieMetodWysylkowych


def test_metody_z_powiazaniami_platnicy():
    gen = GenerowanieMetodWysylkowych()
    gen.dodaj_metode_wysylkowa('X-TARWS', 'Wysyłka do Tarnobrzegu - Szpital Wojewódzki - ALAB', aparat='X-WYSYL')
    gen.dodaj_powiazanie_metody('AN-ACIP', 'X-TARWS', system='CHELM')
    gen.dodaj_powiazanie_metody('AN-ACIR', 'X-TARWS', system='CHELM')
    with open(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'testowy_dat_metody_wysylkowe.dat'
    ), 'rb') as f:
        target_content = f.read().strip()
    assert gen.render_dat().decode('cp1250').strip() == target_content.decode('cp1250')
