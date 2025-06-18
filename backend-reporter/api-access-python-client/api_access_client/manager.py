import datetime
import os
import json
import time
import requests

from . import utils

try:
    import aiohttp

    AIO_HTTP_AVAILABLE = True
except ImportError:
    AIO_HTTP_AVAILABLE = False


class ServerAppInstance:
    def __init__(self, app, name):
        self.app = app
        self.name = name
        self.cfg = None
        self.refreshed = True
        self.forced_url = None

    def refresh_cfg(self, cfg):
        self.cfg = cfg
        self.refreshed = True

    def check_token(self):
        if 'token' in self.cfg:
            if not utils.is_token_valid(self.cfg['token']):
                if not self.app.manager.refresh_config():
                    return False
        return self.refreshed

    def force_url(self, url):
        self.forced_url = url

    def request(self, method, url, **kwargs):
        url = self._full_url(url)
        if 'token' in self.cfg:
            self.check_token()
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            kwargs['headers']['Authorization'] = 'Bearer %s' % self.cfg['token']
        if self.app.manager.allow_unsafe_ssl:
            kwargs['verify'] = False
            requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
        response = requests.request(method, url, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError("Service response code %d, %s" % (response.status_code, response.content.decode()))
        return response

    async def async_request(self, method, url, **kwargs):
        if not AIO_HTTP_AVAILABLE:
            raise RuntimeError('No aiohttp module')
        url = self._full_url(url)
        if 'token' in self.cfg:
            self.check_token()
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            kwargs['headers']['Authorization'] = 'Bearer %s' % self.cfg['token']
            if self.app.manager.allow_unsafe_ssl:
                kwargs['verify'] = False
            async with aiohttp.request(method, url, **kwargs) as request:
                try:
                    resp = await request.json()
                    return resp
                except:
                    print(resp.headers)
                    print(resp.content)
                    raise

    def get_json(self, url, **kwargs):
        resp = self.request('GET', url, **kwargs)
        try:
            return resp.json()
        except:
            print(resp.content.decode('ascii', 'ignore'))
            raise

    def post_json(self, url, data, **kwargs):
        resp = self.request('POST', url, json=data, **kwargs)
        try:
            return resp.json()
        except:
            print(resp.content.decode('ascii', 'ignore'))
            raise

    async def async_get_json(self, url, **kwargs):
        return await self.async_request('GET', url, **kwargs)

    async def async_post_json(self, url, data, **kwargs):
        return await self.async_request('POST', url, json=data, **kwargs)

    def _full_url(self, url):
        if '://' in url:
            return url
        if self.forced_url is not None:
            base_url = self.forced_url
        else:
            if 'urls' not in self.cfg or len(self.cfg['urls']) == 0:
                raise ValueError('No urls in app config - must provide full URL')
            base_url = utils.get_best_url(self.cfg['urls'])
        if base_url.endswith('/') and url.startswith('/'):
            return base_url + url[1:]
        if not base_url.endswith('/') and not url.startswith('/'):
            return base_url + '/' + url
        return base_url + url


class ServerApp:
    def __init__(self, api_access_manager, name):
        self.manager = api_access_manager
        self.name = name
        self.instances = {}
        self.refreshed = True

    def load_instance_config(self, cfg):
        self.refreshed = True
        instance_name = cfg['app_instance']
        if instance_name not in self.instances:
            self.instances[instance_name] = ServerAppInstance(self, instance_name)
        self.instances[instance_name].refresh_cfg(cfg)

    def _reset_refreshed(self):
        self.refreshed = False
        for _, inst in self.instances.items():
            inst.refreshed = False

    def _delete_not_refreshed(self):
        to_delete = [name for name, inst in self.instances.items() if not inst.refreshed]
        for name in to_delete:
            del self.instances[name]


class ApiAccessManager:
    def __init__(self, api_access_url=None, refresh_token=None, access_config_filename=None):
        self.api_access_url = api_access_url
        self.refresh_token = refresh_token
        self.access_config_filename = access_config_filename
        self.app_name = None
        self.app_instance = None
        self.server_apps = {}
        self.allow_unsafe_ssl = False
        if self.api_access_url is None:
            from config import Config
            self.api_access_url = Config.API_ACCESS_URL
            if self.refresh_token is None:
                self.refresh_token = Config.API_ACCESS_REFRESH_TOKEN
            if self.access_config_filename is None and hasattr(Config, 'API_ACCESS_CONFIG_FILENAME'):
                self.access_config_filename = Config.API_ACCESS_CONFIG_FILENAME
        if self.access_config_filename is None:
            self.access_config_filename = utils.get_default_access_config_filename(self.refresh_token)
        elif os.path.isdir(self.access_config_filename):
            self.access_config_filename = utils.get_default_access_config_filename(self.refresh_token,
                                                                                   base_dir=self.access_config_filename)
        self._remove_old_config_file()
        if not self.load_config():
            self.refresh_config()

    def _remove_old_config_file(self):
        if os.path.exists(self.access_config_filename):
            st = os.stat(self.access_config_filename)
            if time.time() - st.st_mtime > 8 * 3600:
                self.clean_config()

    def clean_config(self):
        if os.path.exists(self.access_config_filename):
            os.unlink(self.access_config_filename)

    def load_config(self, data=None):
        if data is None and os.path.exists(self.access_config_filename):
            with open(self.access_config_filename, 'r') as f:
                data = json.load(f)
        if data is None:
            return False
        self.app_name = data.get('app_name')
        self.app_instance = data.get('app_instance')
        # TODO: api powinno zwracać wartość swojego zegara, żeby tu policzyć ew. poślizg, do liczenia ważności tokenów
        self._reset_refreshed()
        for access_config in data.get('access', []):
            self._load_instance_config(access_config)
        self._delete_not_refreshed()
        return True

    def _reset_refreshed(self):
        for _, app in self.server_apps.items():
            app._reset_refreshed()

    def _delete_not_refreshed(self):
        to_delete = []
        for name, app in self.server_apps.items():
            if not app.refreshed:
                to_delete.append(name)
            else:
                app._delete_not_refreshed()
        for name in to_delete:
            del self.server_apps[name]

    def _load_instance_config(self, cfg):
        app_name = cfg['app_name']
        if app_name not in self.server_apps:
            self.server_apps[app_name] = ServerApp(self, app_name)
        self.server_apps[app_name].load_instance_config(cfg)

    def _get_config_from_api_access_api(self):
        resp = requests.get(self.api_access_url, headers={
            'Authorization': 'Bearer %s' % self.refresh_token,
        })
        try:
            return resp.json()
        except:
            with open('/tmp/api_access_last_error.html', 'wb') as f:
                f.write(resp.content)
            raise

    def refresh_config(self):
        refreshing_fn = self.access_config_filename + '.refreshing'
        if os.path.exists(refreshing_fn):
            for _ in range(5):
                time.sleep(1)
                if not os.path.exists(refreshing_fn):
                    break
            if self.load_config():
                return True
        try:
            with open(refreshing_fn, 'w') as f:
                f.write('%d %s' % (os.getpid(), str(datetime.datetime.now())))
            data = self._get_config_from_api_access_api()
            if data['status'] == 'ok':
                self.load_config(data)
                with open(self.access_config_filename, 'w') as f:
                    json.dump(data, f)
                return True
            return False
        finally:
            os.unlink(refreshing_fn)

    def get_apps(self):
        return self.server_apps.keys()

    def get_instances(self, app_name):
        if app_name not in self.server_apps:
            return []
        return self.server_apps[app_name].instances.keys()

    def __getitem__(self, item):
        app_name = item
        instance_name = None
        if isinstance(app_name, tuple):
            app_name, instance_name = app_name
        if app_name not in self.server_apps:
            return None
        if instance_name is not None:
            if instance_name not in self.server_apps[app_name].instances:
                return None
            return self.server_apps[app_name].instances[instance_name]
        else:
            for _, inst in self.server_apps[app_name].instances.items():
                return inst
