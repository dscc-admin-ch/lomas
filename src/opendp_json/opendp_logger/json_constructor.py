import opendp_json.opendp_logger.json_trans as json_trans
import opendp_json.opendp_logger.json_meas as json_meas
import opendp_json.opendp_logger.json_comb as json_comb

from typing import Literal
import json
import yaml
import re
import builtins

PT_TYPE = "^py_type:*"

from opendp_json.opendp_logger import OPENDP_VERSION

blocklist = {
    "Measurement": [],
    "Transformation": []
}

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
        module = json_trans
    elif branch["module"] == "meas":
        module = json_meas
    elif branch["module"] == "comb":
        args = list(branch["args"])
        for i in range(len(branch["args"])):
            if isinstance(args[i], dict):
                args[i] = tree_walker(args[i])
        branch["args"] = tuple(args)

        for k, v in branch["kwargs"]:
            if isinstance(v, dict):
                branch["kwargs"][k] = tree_walker(v)

        module = json_comb
    else:
        raise ValueError(f"Type {branch['type']} not in Literal[\"Transformation\", \"Measurement\"].")
    
    return getattr(module, branch["func"])(*branch["args"], **branch["kwargs"])

def opendp_constructor(parse_str: str, ptype: Literal["json", "yaml"]):
    if ptype == "json":
        obj = json.loads(parse_str, object_hook=jsonOpenDPDecoder)
    elif ptype == "yaml":
        obj = cast_str_to_type(yaml.load(parse_str))
    else:
        raise ValueError("Can only parse json and yaml formats.")

    if obj["version"] != OPENDP_VERSION:
        raise ValueError(
            f"OpenDP version in parsed object ({obj['version']}) does not match the current installation ({OPENDP_VERSION})."
            )
    
    return tree_walker(obj["ast"])
