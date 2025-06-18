import json
from tasks.db import redis_conn


def get_and_cache(ident, executor, timeout=300, args=None):
    if args is None:
        args = []
    ident = 'cache:' + ident
    res = redis_conn.get(ident)
    if res is not None:
        return json.loads(res.decode())
    else:
        res = executor(*args)
        redis_conn.set(ident, json.dumps(res), ex=timeout)
        return res
