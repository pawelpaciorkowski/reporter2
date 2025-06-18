from rapidfuzz import fuzz, process

from datasources.reporter import ReporterDatasource
from plugins import PluginManager
from helpers import get_and_cache


def menu_for_user(user_login, user_permissions):
    index_l1 = {}
    index_l2 = {}

    plugin_manager = PluginManager.singleton()

    def walk(menu_item, breadcrumb):
        nonlocal index_l1, index_l2
        if isinstance(menu_item, list):
            for item in menu_item:
                walk(item, breadcrumb)
            return
        path = '/' + menu_item['path']
        title = menu_item.get('menu_entry', path) or '???'
        texts_l1, texts_l2 = plugin_manager.get_search_texts(menu_item['module'])
        for index, texts in zip([index_l1, index_l2], [texts_l1, texts_l2]):
            text = ' '.join(texts).lower()
            if text not in index:
                index[text] = []
            index[text].append((path, title, ' » '.join(breadcrumb)))
        if 'children' in menu_item and isinstance(menu_item['children'], list):
            for item in menu_item['children']:
                walk(item, breadcrumb + [title])

    walk(plugin_manager.get_menu_for_user(user_permissions), [])
    return index_l1, index_l2


def reports_for_user(user_login, user_permissions):
    res = {}
    plugin_manager = PluginManager.singleton()

    def walk(menu_item, breadcrumb):
        nonlocal res
        if isinstance(menu_item, list):
            for item in menu_item:
                walk(item, breadcrumb)
            return
        path = '/' + menu_item['path']
        title = menu_item.get('menu_entry', path) or '???'
        res[path] = (title, ' » '.join(breadcrumb))
        if 'children' in menu_item and isinstance(menu_item['children'], list):
            for item in menu_item['children']:
                walk(item, breadcrumb + [title])

    walk(plugin_manager.get_menu_for_user(user_permissions), [])
    return res


def search_in_menu(user_login, user_permissions, query):
    results = []
    index_l1, index_l2 = get_and_cache(
        'menu_for_user_%s' % user_login,
        lambda: menu_for_user(user_login, user_permissions),
        timeout=3600,
    )
    path_in_results = set()
    for index in (index_l1, index_l2):
        if len(results) == 10:
            break
        for text, score, _ in process.extract(query, index.keys(), scorer=fuzz.partial_token_sort_ratio,
                                              score_cutoff=20):
            if len(results) == 10:
                break
            for path, title, breadcrumb in index[text]:
                if path in path_in_results:
                    continue
                path_in_results.add(path)
                results.append({
                    'title': title,
                    'helper': breadcrumb,
                    'url': path,
                })

    return results


def recent_reports_for_user(user_login, user_permissions):
    rfu = get_and_cache(
        'reports_for_user_%s' % user_login,
        lambda: reports_for_user(user_login, user_permissions),
        timeout=3600,
    )
    rep = ReporterDatasource()
    sql = """
        select max(id) as max_id, opis from (
        select id, opis 
        from log_zdarzenia 
        where id>(select id from log_zdarzenia order by id desc limit 1)-10000
        and obj_type='osoba' and obj_id=(select id from osoby where login=%s) and typ='REPGEN'
        order by id desc) a 
        group by opis
        order by max(id) desc
        limit 5
    """
    res = []
    for row in rep.dict_select(sql, [user_login]):
        path = '/' + row['opis'].replace('.', '/')
        if path in rfu:
            title, breadcrumb = rfu[path]
            res.append({
                'title': title,
                'helper': breadcrumb,
                'url': path
            })
    return res


def recent_reports(user_login, user_permissions):
    result = get_and_cache(
        'recent_reports_for_user_%s' % user_login,
        lambda: recent_reports_for_user(user_login, user_permissions),
        timeout=60
    )
    return result
