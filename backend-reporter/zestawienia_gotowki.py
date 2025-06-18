# TODO: zrobić z tego i z nocka_sync jakiś pojedynczy commandlinowy programek

import sys
from plugins import PluginManager


def zrob_zestawienia_zeszly_miesiac(katalog):
    pm = PluginManager()

    plugin = pm.find_plugin_by_path('meta.backend.zestawienia_gotowki')
    plugin.zrob_zestawienia_zeszly_miesiac(katalog)


if __name__ == '__main__':
    zrob_zestawienia_zeszly_miesiac(sys.argv[1])
