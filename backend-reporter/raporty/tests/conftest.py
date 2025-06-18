import pytest
import plugins

pm = None


def all_plugins():
    global pm
    if pm is None:
        pm = plugins.PluginManager()
    res = []

    def walk_plugins(plugin):
        if isinstance(plugin, list):
            for elem in plugin:
                walk_plugins(elem)
        elif isinstance(plugin, dict):
            if 'module' in plugin:
                res.append(plugin['module'])
            if 'children' in plugin:
                walk_plugins(plugin['children'])

    walk_plugins(pm.plugins)
    return res


def all_plugins_with_dialogs():
    res = []
    for plugin in all_plugins():
        if hasattr(plugin, 'LAUNCH_DIALOG') and plugin.LAUNCH_DIALOG is not None:
            res.append(plugin)
    return res


@pytest.fixture(params=all_plugins_with_dialogs())
def plugin_with_dialog(request):
    return request.param
