import sys
from plugins import PluginManager


def synchronizuj_listy_robocze():
    pm = PluginManager()
    plugin = pm.find_plugin_by_path('meta.backend.listyrobocze_sync')
    plugin.synchronizuj_listy_robocze()


if __name__ == '__main__':
    synchronizuj_listy_robocze()
