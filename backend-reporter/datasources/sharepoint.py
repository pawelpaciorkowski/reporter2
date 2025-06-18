import os
import time

import requests


TTL = 3600
TTL_FALLBACK = 3600 * 48
PROXY_URL = "http://2.0.204.157:8080/"
CACHE_DIR = "/tmp/sharepoint_cache"

def sharepoint_filename(fn):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, 0o755, exist_ok=True)
    res = None
    try_to_refresh = True
    cached_fn = os.path.join(CACHE_DIR, fn)
    if os.path.exists(cached_fn):
        mtime = os.path.getmtime(cached_fn)
        if time.time() - mtime > TTL_FALLBACK:
            os.remove(cached_fn)
        else:
            res = cached_fn
            if time.time() - mtime < TTL:
                try_to_refresh = False
    if try_to_refresh:
        resp = requests.get(PROXY_URL + fn)
        if resp.status_code == 200:
            with open(cached_fn, 'wb') as f:
                f.write(resp.content)
            res = cached_fn
    return res


