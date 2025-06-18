import json
from typing import Union, List

import netifaces

from api.common import get_db
from helpers import prepare_for_json


def divide_chunks(data, chunk_size=64):
    chunks = []
    chunk = []
    for elem in data:
        if len(chunk) == chunk_size:
            chunks.append(chunk)
            chunk = []
        chunk.append(elem)
    if (len(chunk)) > 0:
        chunks.append(chunk)
    return chunks


def divide_by_key(data, key):
    res = {}
    for row in data:
        kv = key(row)
        if kv not in res:
            res[kv] = []
        res[kv].append(row)
    return list(res.values())


def is_lab_avail(lab, labs_available):
    return lab in labs_available or '*' in labs_available


def first_or_none(src):
    if not isinstance(src, list):
        return None
    if len(src) == 0:
        return None
    return src[0]


def get_local_open_vpn_address():
    interfaces = netifaces.interfaces()
    addresses = [netifaces.ifaddresses(i) for i in interfaces]
    addrs = [[a[b] for b in a] for a in addresses]
    addrs_nested = [[b[0]['addr'] for b in a] for a in addrs]
    addrs_list = [j for i in addrs_nested for j in i]

    for address in addrs_list:
        if address.startswith('2.0'):
            return address

    for address in addrs_list:
        if address.startswith('2.128'):
            return address

    return None


def remove_first_cols(cols, rows, ncols):
    return cols[ncols:], [row[ncols:] for row in rows]


def group_by_first_cols(ncols):
    return ' group by ' + ', '.join([str(i + 1) for i in range(ncols)])


def log(obj_type: str, obj_id: int, opis: str,
        typ: str, old_values: Union[List[dict], dict], task_params: dict):

    with get_db() as rep_db:
        rep_db.execute("""insert into log_zdarzenia(obj_type, obj_id, typ, opis, parametry)
            values(%s, %s, %s, %s, %s)
        """, [
            obj_type,
            obj_id,
            typ,
            opis,
            json.dumps(prepare_for_json({
                'row': old_values,
                'task_params': task_params,
            }))
        ])
        rep_db.commit()
