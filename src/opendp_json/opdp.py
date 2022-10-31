import opendp.combinators as comb
import opendp.measurements as meas
import opendp.transformations  as trans
from opendp.mod import enable_features
enable_features('contrib')
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
    
    print(module)
    print(dir(module))
    import inspect
    print(inspect.getsource(getattr(module, branch["func"])))

    return getattr(module, branch["func"])(*branch["args"], **branch["kwargs"])

def opendp_constructor(parse_str: str):
    obj = json.loads(parse_str, object_hook=jsonOpenDPDecoder)

    if obj["version"] != globals.OPENDP_VERSION:
        raise ValueError(
            f"OpenDP version in parsed object ({obj['version']}) does not match the current installation ({globals.OPENDP_VERSION})."
            )
    
    return tree_walker(obj["ast"])


def opendp_apply(opdp_pipe):
    return opdp_pipe("1,2,3,4")