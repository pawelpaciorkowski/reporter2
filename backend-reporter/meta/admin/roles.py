from helpers import prepare_for_json
from plugins import ROLE_CONTAINMENT
from api.common import get_db
from api.restplus import api

MENU_ENTRY = 'Role użytkowników'
REQUIRE_ROLE = ['C-CS', 'R-CS']
GUI_MODE = 'one_shot'

def get_content(user_login):
    data = []
    with get_db() as db:
        for row in db.select('select * from role order by symbol'):
            subroles = ROLE_CONTAINMENT.get(row['symbol'], [])
            zmiana = True
            while zmiana:
                zmiana = False
                for role in subroles:
                    if role in ROLE_CONTAINMENT:
                        for subrole in ROLE_CONTAINMENT[role]:
                            if subrole not in subroles:
                                subroles.append(subrole)
                                zmiana = True
            data.append([row['symbol'], row['nazwa'], ' '.join(subroles)])
    return [
        {
            'type': 'table',
            'title': 'Role użytkowników',
            'header': ['Symbol', 'Nazwa', 'Zawiera role'],
            'data': prepare_for_json(data)
        }
    ]
