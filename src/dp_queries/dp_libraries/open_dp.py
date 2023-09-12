import json
import re
import builtins

import globals

from fastapi import HTTPException
import opendp.combinators as comb
import opendp.measurements as meas
import opendp.transformations as trans
from opendp.mod import enable_features
from typing import List

from dp_queries.dp_logic import DPQuerier
from utils.constants import DUMMY_NB_ROWS, DUMMY_SEED
from utils.loggr import LOG

enable_features("contrib")

PT_TYPE = "^py_type:*"


class OpenDPQuerier(DPQuerier):
    def __init__(
        self,
        metadata,
        private_db,
        dummy: bool = False,
        dummy_nb_rows: int = DUMMY_NB_ROWS,
        dummy_seed: int = DUMMY_SEED,
    ) -> None:
        super().__init__(
            metadata, private_db, dummy, dummy_nb_rows, dummy_seed
        )

    def cost(self, query_json: dict) -> List[float]:
        opendp_pipe = opendp_pipe_constructor(query_json.opendp_json)

        try:
            epsilon, delta = opendp_pipe.map(d_in=1.0)
        except Exception:
            try:
                epsilon, delta = opendp_pipe.map(d_in=1)
            except Exception as e:
                LOG.exception(e)
                raise HTTPException(
                    400,
                    "Error obtaining privacy map for the chain. \
                        Please ensure methods return epsilon, \
                            and delta in privacy map. Error:"
                    + str(e),
                )
        return [epsilon, delta]

    def query(self, query_json: dict) -> str:
        opendp_pipe = opendp_pipe_constructor(query_json.opendp_json)

        try:
            # response, privacy_map = opendp_apply(opendp_pipe)
            release_data = opendp_pipe(self.df.to_csv())
        except HTTPException as he:
            LOG.exception(he)
            raise he
        except Exception as e:
            LOG.exception(e)
            raise HTTPException(
                400,
                "Failed when applying chain to data with error: " + str(e),
            )
        return str(release_data)


def opendp_pipe_constructor(opendp_json: dict) -> None:
    try:
        obj = json.loads(
            opendp_json.toJSONStr(), object_hook=jsonOpenDPDecoder
        )
    except Exception as e:
        LOG.exception(e)
        raise HTTPException(
            500,
            "Failed while contructing opendp pipeline with error: " + str(e),
        )

    if obj["version"] != globals.OPENDP_VERSION:
        raise ValueError(
            f"OpenDP version in parsed object ({obj['version']}) does not\
                match the current installation ({globals.OPENDP_VERSION})."
        )

    try:
        opendp_pipe = tree_walker(obj["ast"])
    except Exception as e:
        LOG.exception(e)
        raise HTTPException(
            500,
            "Failed in opendp tree walker with error: " + str(e),
        )
    return opendp_pipe


def jsonOpenDPDecoder(obj):
    if "_tuple" in obj.keys():
        return tuple(obj["_items"])
    if isinstance(obj, dict):
        return cast_str_to_type(obj)
    return obj


def cast_str_to_type(d):
    for k, v in d.items():
        if isinstance(v, dict):
            cast_str_to_type(v)
        elif isinstance(v, str):
            if re.search(PT_TYPE, v):
                d[k] = getattr(
                    builtins,
                    v[8:],
                )
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
        raise ValueError(
            f"Type {branch['type']} not in \
                Literal[\"Transformation\", \"Measurement\", \"Combination\"]"
        )

    return getattr(module, branch["func"])(
        *branch["args"],
        **branch["kwargs"],
    )
