import opendp.combinators as comb
import opendp.measurements as meas
import opendp.transformations  as trans
from opendp.mod import enable_features
enable_features('contrib')
from fastapi import HTTPException
# print("comb:", comb)
# print("meas:", meas)
# print("trans:", trans)

from typing import Literal
import json
import yaml
import re
import builtins

import globals

PT_TYPE = "^py_type:*"

def cast_str_to_type(d):
    for k, v in d.items():
        if isinstance(v, dict):
            cast_str_to_type(v)
        elif isinstance(v, str):
            if re.search(PT_TYPE, v):
                d[k] = getattr(builtins, v[8:])
    return d

def jsonOpenDPDecoder(obj):
    if "_tuple" in obj.keys():
        return tuple(obj["_items"])
    if isinstance(obj, dict):
        return cast_str_to_type(obj)
    return obj

def cast_type_to_str(d):
    for k, v in d.items():
        if isinstance(v, dict):
            cast_type_to_str(v)
        elif isinstance(v, type):
            d[k] = "pytype_"+str(v.__name__)
    return d

def tree_walker(branch):
    if branch["module"] == "trans":
        module = trans
    elif branch["module"] == "meas":
        module = meas
    elif branch["module"] == "comb":
        args = list(branch["args"])
        for i in range(len(branch["args"])):
            if isinstance(args[i], dict):
                args[i] = tree_walker(args[i])
        branch["args"] = tuple(args)

        for k, v in branch["kwargs"]:
            if isinstance(v, dict):
                branch["kwargs"][k] = tree_walker(v)

        module = comb
    else:
        raise ValueError(f"Type {branch['type']} not in Literal[\"Transformation\", \"Measurement\", \"Combination\"].")

    return getattr(module, branch["func"])(*branch["args"], **branch["kwargs"])

def opendp_constructor(parse_str: str):
    obj = json.loads(parse_str, object_hook=jsonOpenDPDecoder)

    if obj["version"] != globals.OPENDP_VERSION:
        raise ValueError(
            f"OpenDP version in parsed object ({obj['version']}) does not match the current installation ({globals.OPENDP_VERSION})."
            )
    
    return tree_walker(obj["ast"])


def opendp_apply(opdp_pipe):
    try:
        release_data = opdp_pipe(globals.TRAIN.to_csv())
    except Exception as e:
        globals.LOG.exception(e)
        raise HTTPException(400, "Failed when applying chain to data with error: " + str(e))
    try:
        e, d = opdp_pipe.map(d_in=1.)
    except Exception as e:
        globals.LOG.exception(e)
        raise HTTPException(400, 'Error obtaining privacy map for the chain. Please ensure methods return epsilon, and delta in privacy map. Error:' + str(e))
    if e > globals.EPSILON_LIMIT:
        raise HTTPException(400, f"Chain constructed uses epsilon > {globals.EPSILON_LIMIT}, please update and retry")
    if d > globals.DELTA_LIMIT:
        raise HTTPException(400, f"Chain constructed uses delta > {globals.DELTA_LIMIT}, please update and retry")
    return release_data, (e,d)