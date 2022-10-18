import json
from typing import List
from diffprivlib import models
from sklearn.pipeline import Pipeline
import numpy as np
import pandas as pd
import pickle
import pkg_resources

DIFFPRIVLIBP_VERSION = pkg_resources.get_distribution("diffprivlib").version

diffpriv_map = {
    'GaussianNB': models.GaussianNB,
    'KMeans': models.KMeans,
    'LinearRegression': models.LinearRegression,
    'LogisticRegression': models.LogisticRegression,
    'PCA': models.PCA,
    'RandomForestClassifier': models.RandomForestClassifier,
    'StandardScaler': models.StandardScaler
}

#mapping for json key:py_type:tuple to tuple type in python dict
json_pytype_mapping = {
    "tuple": tuple
}

class DiffPrivPipe:
    X_train = np.loadtxt("https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data",
                         usecols=(0, 4, 10, 11, 12), delimiter=", ")

    y_train = np.loadtxt("https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data",
                        usecols=14, dtype=str, delimiter=", ")

    X_test = np.loadtxt("https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.test",
                        usecols=(0, 4, 10, 11, 12), delimiter=", ", skiprows=1)

    y_test = np.loadtxt("https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.test",
                        usecols=14, dtype=str, delimiter=", ", skiprows=1)
    # Must trim trailing period "." from label
    y_test = np.array([a[:-1] for a in y_test])

    def __init__(self, json) -> None:
        self.pipeline_py = self.json_to_pytype(json)
        self.dp_pipeline = self.py_obj_to_pipeline()
        self.fit()

    def json_to_pytype(self, pipeline_json):

        pytype_pipeline_dict = pipeline_json.copy()
        for i, pipeline in enumerate(pytype_pipeline_dict.copy()):
            for k, v in pipeline["kwargs"].copy().items():
                k_split = k.split(":")
                if len(k_split) > 1:
                    del pytype_pipeline_dict[i]["kwargs"][k]
                    pytype_pipeline_dict[i]["kwargs"][k_split[0]
                                                    ] = json_pytype_mapping[k_split[2]](v)
        return pytype_pipeline_dict
    
    #To allow tuple python type - input json -> key:py_type:tuple
    def py_obj_to_pipeline(self):
        dp_pipeline = Pipeline([])
        for pipeline in self.pipeline_py:
            for k, v in pipeline["kwargs"].items():
                k_split = k.split(":")
                if len(k_split) > 1:
                    pipeline["kwargs"][k_split[0]
                                       ] = json_pytype_mapping[k_split[2]](v)
            dp_pipeline.steps.append(
                (pipeline["name"], diffpriv_map[pipeline["model"]]
                (*pipeline["args"], **pipeline["kwargs"])))
        return dp_pipeline

    def fit(self):
        self.dp_pipeline.fit(self.X_train, self.y_train)
    
    def predict(self):
        return self.dp_pipeline.predict(self.X_test)


def dppipe_predict(pipeline_json):

    dp_model = DiffPrivPipe(pipeline_json)
    
    full_model_path = "filename2"
    print(dp_model.dp_pipeline)
    with open(full_model_path, "wb") as model_file:
        pickle.dump(dp_model.dp_pipeline, model_file)

    print(dp_model.dp_pipeline)
    # print(dp_model.dp_pipeline.score(
    #     dp_model.X_test, dp_model.y_test) * 100)
    return full_model_path
    #Creating model file 
    # stream = io.StringIO()
    # CSV creation
    # predicted_res = dp.predict()
     
    # predicted_res = pd.DataFrame(predicted_res).to_csv(stream, index=False)
    # response = StreamingResponse(
    #     iter([stream.getvalue()]),
    #     media_type="text/csv"
    # )
    # response.headers["Content-Disposition"] = "attachment; filename=diffprivlib_predictions.csv"
    
    return response
