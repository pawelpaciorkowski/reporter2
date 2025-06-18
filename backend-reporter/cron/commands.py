import inspect
import datetime

REGISTERING_ENABLED = False
COMMAND_REGISTRY = []


def set_registering_enabled():
    global REGISTERING_ENABLED
    REGISTERING_ENABLED = True


def get_command_registry():
    global COMMAND_REGISTRY
    return COMMAND_REGISTRY


class RegisterCommand:
    def __init__(self, min=None, hour=None, day_of_month=None, month=None, day_of_week=None, **kwargs):
        if not REGISTERING_ENABLED:
            return
        print('RC init', min, hour, day_of_month, month, day_of_week, kwargs)
        self.min = min
        self.hour = hour
        self.day_of_month = day_of_month
        self.month = month
        self.day_of_week = day_of_week

    def __call__(self, fn):
        global COMMAND_REGISTRY
        if not REGISTERING_ENABLED:
            return fn
        mod = inspect.getmodule(fn)
        print('RC call',
              fn)  # , mod.__dict__['__PLUGIN__']) -- TODO: tego jeszcez nie ma - jest dopiero po załadowaniu plugin managera
        self.fn = fn
        COMMAND_REGISTRY.append(self)
        return fn

    def get_next_run(self, previous_run):
        date = datetime.datetime.now()
        if previous_run is None:
            return date


    def should_run(self, previous_run):
        return self.get_next_run(previous_run) <= datetime.datetime.now()
