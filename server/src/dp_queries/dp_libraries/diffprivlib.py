from io import BytesIO
from typing import List
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import diffprivlib
import pickle
import json

from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset
from utils.loggr import LOG

class DiffPrivLibQuerier(DPQuerier):
    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        super().__init__(private_dataset)

    def cost(self, query_json: dict) -> List[float]:
        # Reconstruct pipeline
        try:
            dpl_pipeline = deserialise_pipeline(query_json.diffprivlib_json)
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as exc:
            LOG.error(exc)
            raise exc
        
        # Compute budget
        spent_epsilon = 0
        spent_delta = 0
        for step in dpl_pipeline.steps:
            spent_epsilon += step[1].accountant.spent_budget[0][0]
            spent_delta += step[1].accountant.spent_budget[0][1]

        return spent_epsilon, spent_delta

    def query(self, query_json: dict) -> str:
        
        # Reconstruct pipeline
        try:
            dpl_pipeline = deserialise_pipeline(query_json.diffprivlib_json)
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as exc:
            LOG.error(exc)
            raise exc

        # Prepare data
        data = self.private_dataset.get_pandas_df()
        feature_data = data[query_json.feature_columns]
        label_data = data[query_json.target_columns]
        x_train, x_test, y_train, y_test = train_test_split(
            feature_data, 
            label_data, 
            test_size = query_json.test_size,
            random_state = query_json.test_train_split_seed
        )
        
        # Train model
        try:
            dpl_pipeline.fit(x_train, y_train) 
        except Exception as e:
            LOG.exception(f"Cannot train model error: {str(e)}")
            raise HTTPException(500, f"Cannot train model error: {str(e)}")
        
        # Serialise model
        pickled_model = pickle.dumps(dpl_pipeline)
        
        # Estimate accuracy
        accuracy = dpl_pipeline.score(x_test, y_test)

        # Prepare response
        response = {
            "model": pickled_model,
            "accuracy": accuracy
        }
        return response


class DiffPrivLibDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, dct):
        if "_tuple" in dct.keys():
            return tuple(dct["_items"])

        for k, v in dct.items():
            if type(v) is str:
                if v[:10] == "_dpl_type:":
                    try:
                        dct[k] = getattr(diffprivlib.models, v[10:])
                    except Exception as e:
                        LOG.exception(e)

                elif v[:14] == "_dpl_instance:":
                    try:
                        dct[k] = getattr(diffprivlib, v[14:])()
                    except Exception as e:
                        LOG.exception(e)

        return dct


def deserialise_pipeline(diffprivlib_json):
    dct = json.loads(diffprivlib_json, cls=DiffPrivLibDecoder)
    if "module" in dct.keys():
        if dct["module"] != "diffprivlib":
            raise ValueError("JSON 'module' not equal to 'diffprivlib', maybe you sent the request to the wrong path.")
    else:
        raise ValueError("Key 'module' not in submitted json request.")

    if "version" in dct.keys():
        if dct["version"] != diffprivlib.__version__:
            raise ValueError(f"The version of requested does not match the version available: {diffprivlib.__version__}.")
    else:
        raise ValueError("Key 'version' not in submitted json request.")

    return Pipeline(
        [(val["name"], val["type"](**val["params"])) for val in dct["pipeline"]]
    )
