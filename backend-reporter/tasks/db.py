import json
import redis
from rq import Worker, Queue, Connection
from rq.job import Job

redis_url = 'redis://localhost:6379'

redis_conn = redis.from_url(redis_url)
rq_conn = Connection(redis_conn)


def save_user_task_group(login, ident):
    redis_conn.sadd('rutg:%s' % login, ident)


def drop_user_task_group(login, ident):
    redis_conn.srem('rutg:%s' % login, ident)


def save_task_group(ident, params):
    redis_conn.set('rtg:%s' % ident, json.dumps(params))


def load_task_group(ident):
    res = redis_conn.get('rtg:%s' % ident)
    if res is not None:
        return json.loads(res)
    else:
        return None


def fetch_job(job_id):
    return Job.fetch(job_id, connection=redis_conn)
