import diffprivlib
from sklearn.pipeline import Pipeline
import inspect
import json


class DiffprivlibEncoder(json.JSONEncoder):
    def default(self, obj):
        types = [
            v[1] for v in inspect.getmembers(diffprivlib, inspect.isclass)
        ]
        if type(obj) in types:
            return "_dpl_instance:" + obj.__class__.__name__
        else:
            return super().default(obj)

    def encode(self, obj) -> str:
        def hint_tuples(item):
            if isinstance(item, tuple):
                return {"_tuple": True, "_items": item}
            if isinstance(item, list):
                return [hint_tuples(e) for e in item]
            if isinstance(item, dict):
                return {key: hint_tuples(value) for key, value in item.items()}
            else:
                return item

        return super().encode(hint_tuples(obj))


def serialize_diffprivlib(pipeline: Pipeline):
    assert isinstance(pipeline, Pipeline)
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
