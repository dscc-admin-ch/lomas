import inspect
import json

import diffprivlib
from sklearn.pipeline import Pipeline


class DiffprivlibEncoder(json.JSONEncoder):
    """Overwrites JSON Encoder class to serialise DiffPrivLib
    pipelines with a specific format.
    """

    def default(self, o: dict):
        """Extends JSON encoder to DiffPrivLib class members"""
        types = [
            v[1] for v in inspect.getmembers(diffprivlib, inspect.isclass)
        ]
        if type(o) in types:
            return "_dpl_instance:" + o.__class__.__name__
        return super().default(o)  # regular json encoding

    def encode(self, o: dict) -> str:
        """Define JSON string representation of a DiffPrivLib pipeline"""

        def hint_tuples(item):
            if isinstance(item, tuple):
                return {"_tuple": True, "_items": item}
            if isinstance(item, list):
                return [hint_tuples(e) for e in item]
            if isinstance(item, dict):
                return {key: hint_tuples(value) for key, value in item.items()}
            return item

        return super().encode(hint_tuples(o))


def serialize_diffprivlib(pipeline: Pipeline):
    """Serialise the DiffPrivLib pipeline to send it through FastAPI

    Args:
        pipeline (Pipeline): a DiffPrivLib pipeline

    Raises:
        ValueError: If the input argument is not a scikit-learn pipeline.

    Returns:
        serialised (str): DiffPivLib pipeline as a serialised string
    """
    if not isinstance(pipeline, Pipeline):
        raise ValueError(
            "Input pipeline must be an instance of sklearn.pipeline.Pipeline"
        )

    json_body = {
        "module": "diffprivlib",
        "version": diffprivlib.__version__,
        "pipeline": [],
    }

    for step_name, step_fn in pipeline.steps:
        dict_params = vars(step_fn)
        params = list(inspect.signature(type(step_fn)).parameters)
        dict_params = {k: v for k, v in dict_params.items() if k in params}
        json_body["pipeline"].append(
            {
                "type": "_dpl_type:" + step_fn.__class__.__name__,
                "name": step_name,
                "params": dict_params,
            }
        )

    return json.dumps(json_body, cls=DiffprivlibEncoder)
