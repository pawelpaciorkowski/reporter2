from plugins import PluginManager
# from .commands import set_registering_enabled, get_command_registry
from .cronjobs import CronJobManager, CronJob
import config

cfg = config.Config()

if cfg.SENTRY_URL is not None:
    import sentry_sdk

    sentry_sdk.init(cfg.SENTRY_URL)


def main():
    pm = PluginManager(lazy=True)
    cjm = CronJobManager(pm)
    cjm.collect_results()
    cjm.start_new_jobs()
