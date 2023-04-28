from io import BytesIO
import json
import pickle
from fastapi import HTTPException

from fastapi.responses import StreamingResponse
import pkg_resources
from diffprivlib import models
from sklearn.pipeline import Pipeline

import globals
from loggr import LOG
import diffprivlib

DIFFPRIVLIBP_VERSION = pkg_resources.get_distribution("diffprivlib").version

diffpriv_map = {
    "_dpl_type:GaussianNB": models.GaussianNB,
    "_dpl_type:KMeans": models.KMeans,
    "_dpl_type:LinearRegression": models.LinearRegression,
    "_dpl_type:LogisticRegression": models.LogisticRegression,
    "_dpl_type:PCA": models.PCA,
    "_dpl_type:RandomForestClassifier": models.RandomForestClassifier,
    "_dpl_type:StandardScaler": models.StandardScaler,
}

# mapping for json key:py_type:tuple to tuple type in python dict
json_pytype_mapping = {"tuple": tuple}


class DiffPrivPipe:
    def __init__(self, json) -> None:
        self.pipeline_py = self.json_to_pytype(json)
        self.dp_pipeline = self.py_obj_to_pipeline()
        self.fit()

    def json_to_pytype(self, pipeline_json):

        pytype_pipeline_dict = pipeline_json.copy()
        for (
            i,
            pipeline,
        ) in enumerate(pytype_pipeline_dict.copy()):
            for k, v in pipeline["kwargs"].copy().items():
                k_split = k.split(":")
                if len(k_split) > 1:
                    del pytype_pipeline_dict[i]["kwargs"][k]
                    pytype_pipeline_dict[i]["kwargs"][
                        k_split[0]
                    ] = json_pytype_mapping[k_split[2]](v)
        return pytype_pipeline_dict

    # To allow tuple python type - input json -> key:py_type:tuple
    def py_obj_to_pipeline(
        self,
    ):
        dp_pipeline = Pipeline([])
        for pipeline in self.pipeline_py:
            for (
                k,
                v,
            ) in pipeline["kwargs"].items():
                k_split = k.split(":")
                if len(k_split) > 1:
                    pipeline["kwargs"][k_split[0]] = json_pytype_mapping[
                        k_split[2]
                    ](v)
            dp_pipeline.steps.append(
                (
                    pipeline["name"],
                    diffpriv_map[pipeline["model"]](
                        *pipeline["args"],
                        **pipeline["kwargs"],
                    ),
                )
            )
        return dp_pipeline

    def fit(self):
        self.dp_pipeline.fit(
            globals.TRAIN_X.to_numpy(),
            globals.TRAIN_Y.to_numpy(),
        )

    def predict(self):
        return self.dp_pipeline.predict(globals.TEST_X.to_numpy())


def dppipe_predict(
    pipeline_json,
):

    dp_model = DiffPrivPipe(pipeline_json)

    pickled_model = pickle.dumps(dp_model.dp_pipeline)
    # dp_model_score = (
    #    dp_model.dp_pipeline.score(
    #        globals.TEST_X.to_numpy(),
    #        globals.TEST_Y.to_numpy(),
    #    )
    #    * 100
    # )
    # reponse_log = {
    #    "score": dp_model_score,
    #    "model_pickle": pickled_model,
    # }

    # Taking buget from BudgetAccountant of first pipeline models
    budget = dp_model.dp_pipeline.steps[0][1].accountant.spent_budget

    # print(dp_model.dp_pipeline.score(
    #     dp_model.X_test, dp_model.y_test) * 100)
    response = StreamingResponse(BytesIO(pickled_model))
    response.headers[
        "Content-Disposition"
    ] = "attachment; filename=diffprivlib_trained_pipeline.pkl"

    return response, budget


def dppipe_deserielize_train(pipeline_json, y_column=""):
    try:
        dp_pipe = deserialize_pipeline(pipeline_json)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as exc:
        LOG.error(exc)
        raise exc

    try:
        dp_pipe.fit(
            globals.TRAIN_X,
            globals.TRAIN_Y[y_column],
        )
    except Exception as e:
        LOG.exception(f"Cannot train model error: {str(e)}")
        raise HTTPException(
            500,
            f"Cannot train model error: {str(e)}",
        )

    pickled_pipe = pickle.dumps(dp_pipe)
    accuracy = dp_pipe.score(
        globals.TEST_X,
        globals.TEST_Y[y_column],
    )
    pkl_response = StreamingResponse(BytesIO(bytes(pickled_pipe)))
    pkl_response.headers[
        "Content-Disposition"
    ] = "attachment; filename=diffprivlib_trained_pipeline.pkl"

    spent_budget = {
        "epsilon": 0,
        "delta": 0,
    }
    for step in dp_pipe.steps:
        spent_budget["epsilon"] += step[1].accountant.spent_budget[0][0]
        spent_budget["delta"] += step[1].accountant.spent_budget[0][1]

    if spent_budget["epsilon"] > globals.EPSILON_LIMIT:
        raise HTTPException(
            400,
            f"Pipeline constructed uses epsilon > {globals.EPSILON_LIMIT}, \
                please update and retry",
        )
    if spent_budget["delta"] > globals.DELTA_LIMIT:
        raise HTTPException(
            400,
            f"Pipeline constructed uses delta > {globals.DELTA_LIMIT}, \
                please update and retry",
        )
    db_response = {
        "pickled_pipe": str(pickled_pipe),
        "accuracy": accuracy,
    }
    return (
        pkl_response,
        spent_budget,
        db_response,
    )


class DPL_Decoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(
            self,
            object_hook=self.object_hook,
            *args,
            **kwargs,
        )

    def object_hook(self, dct):
        if "_tuple" in dct.keys():
            return tuple(dct["_items"])

        for (
            k,
            v,
        ) in dct.items():
            if type(v) is str:
                if v[:10] == "_dpl_type:":
                    try:
                        dct[k] = getattr(
                            diffprivlib.models,
                            v[10:],
                        )
                    except Exception as e:
                        LOG.exception(e)

                elif v[:14] == "_dpl_instance:":
                    try:
                        dct[k] = getattr(
                            diffprivlib,
                            v[14:],
                        )()
                    except Exception as e:
                        LOG.exception(e)

        return dct


def deserialize_pipeline(
    dct_str,
):
    dct = json.loads(
        dct_str,
        cls=DPL_Decoder,
    )
    if "module" in dct.keys():
        if dct["module"] != "diffprivlib":
            raise ValueError(
                "JSON 'module' not equal to 'diffprivlib', \
                    maybe you sent the request to the wrong path."
            )
    else:
        raise ValueError("Key 'module' not in submitted json request.")

    if "version" in dct.keys():
        if dct["version"] != diffprivlib.__version__:
            raise ValueError(
                f"The version of requested does not match the version \
                    available: {diffprivlib.__version__}."
            )
    else:
        raise ValueError("Key 'version' not in submitted json request.")

    return Pipeline(
        [
            (
                val["name"],
                val["type"](**val["params"]),
            )
            for val in dct["pipeline"]
        ]
    )
