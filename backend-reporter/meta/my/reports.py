from api.auth import login_required
from datasources.reporter import ReporterDatasource

MENU_ENTRY = 'Raporty'


@login_required
def submenu_for_user(user_login):
    rep = ReporterDatasource()
    res = []
    for row in rep.dict_select("select * from cron_plan where users like %s", ['%%%s%%' % user_login]):
        if ' %s ' % user_login in ' %s ' % row['users']:
            res.append(('saved_reports:%d' % row['id'], row['name']))
    return res

GUI_MODE = 'saved_reports'

