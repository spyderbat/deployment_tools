from __future__ import annotations

import gzip
import json
from typing import Callable, List




def smart_open(fn, mode):
    if fn.endswith('.gz'):
        return gzip.open(fn, mode)
    else:
        return open(fn, mode)


def last_model(
        rec_list,
        schemas: List[str],
        extra_index_by=["schema"]):
    by_id = {}
    index = {xidx: {} for xidx in extra_index_by}
    maxtime = 0

    for entry in rec_list:
        rec = entry
        try:
            schema = rec['schema']
        except TypeError:
            rec = json.loads(rec)
            schema = rec['schema']
        if schema in schemas:
            maxtime = max(maxtime, rec.get("time", 0))
            by_id[rec['id']] = rec
            for xidx in extra_index_by:
                value = rec[xidx]
                by_value = index[xidx].setdefault(value, {})
                by_value[rec['id']] = rec

    index["id"] = by_id
    index["maxtime"] = maxtime
    return index


# def last_model_from_file(infile, schemas: List[str], extra_index_by: List[str]):
#     with infile:
#         return last_model(infile, schemas, lambda x: json.loads(x), extra_index_by)

# def last_model_from_records(records, schemas: List[str]):
#     return last_model(records, schemas, lambda x: x)





def echo(func):
    def wrap_func(*args, **kwargs):
        echo = (f"{func.__name__!r} -> ")
        try:
            result = func(*args, **kwargs)
            echo += "succeeded"
        except AssertionError as ae:
            echo += "failed"
            raise AssertionError
        print(echo)
        return result
    return wrap_func


