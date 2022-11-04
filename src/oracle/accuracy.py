from fastapi import UploadFile, HTTPException
import pandas as pd
import numpy as np
# from globals import TEST, LEADERBOARD
import globals
from mongodb.db_functions import db_get_budget, db_get_delta

def accuracy(csv_file: UploadFile, x_oblv_user_name:str):
    # now create a temperary dataframe
    tmp_df = pd.read_csv(csv_file.file)

    if "id" not in tmp_df.columns.values:
        raise HTTPException(400, f"id must be a column in the csv file uploaded.")
    
    if tmp_df["id"].is_unique:
        tmp_df.set_index("id", inplace=True)
    else:
        raise HTTPException(400, f"All values in the id column must be unique. This is important for the differential privacy budget.")

    if len(list(tmp_df.columns)) != 1:
        raise HTTPException(400, f"You can only submit 2 columns, one with col name 'id' and on containing the labels.")

    col_name = list(tmp_df.columns)[0]
    tmp_df = tmp_df.rename(columns={col_name:"submitted"})

    joint_data = tmp_df.join(
            globals.TEST,
            how="inner"
        )
    
    acc = (joint_data["submitted"] == joint_data["labels"]).mean()

    eps = db_get_budget(x_oblv_user_name)
    delta = db_get_delta(x_oblv_user_name)
    score = acc + get_loss(eps, delta, globals.TEST.shape[0])

    return acc, score

def get_loss(eps, delta, D, eps_sigma=100, delta_alpha=5, delta_beta=3):
  return - (eps/eps_sigma) - (1 - np.exp( - delta_alpha*delta*D))**delta_beta