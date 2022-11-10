from fastapi import UploadFile, HTTPException
import pandas as pd
import numpy as np
# from globals import TEST, LEADERBOARD
import globals
from mongodb.db_functions import db_get_budget, db_get_delta

def split_df(df):
    if len(df) % 2 != 0:  # Handling `df` with `odd` number of rows
        df = df.iloc[:-1, :]
    df1, df2 =  np.array_split(df, 2)
    return df1, df2


def accuracy(csv_file: UploadFile, x_oblv_user_name:str):


    eps = db_get_budget(x_oblv_user_name)
    if eps == None or eps == {}:
        raise HTTPException(400, "Team entry not found: " + str(x_oblv_user_name) )

    delta = db_get_delta(x_oblv_user_name)

    # now create a temperary dataframe
    try:
        tmp_df = pd.read_csv(csv_file.file)
    except Exception as e:
        raise HTTPException(400, f"Uploaded daata is invalid")

    if tmp_df.shape[0] != globals.TEST_Y.shape[0]:
        raise HTTPException(400, f"Please submit 3 columns, with names {globals.TEST_Y.columns} and same no. of rows as X_test shared")

    if tmp_df.shape[1] != globals.TEST_Y.shape[1]:
        raise HTTPException(400, f"Please submit 3 columns, with names {globals.TEST_Y.columns} and same no. of rows as X_test shared")



    tmp_df_ld, tmp_df_final = split_df(tmp_df)
    test_y_ld, test_y_final = split_df(globals.TEST_Y)

    try:
        acc_ld = float((tmp_df_ld == test_y_ld).mean().mean())

        acc_final = float((tmp_df_final == test_y_final).mean().mean())
    except Exception as excp:
        globals.LOG.exception(excp)
        globals.LOG.error("Error occured while calculating the score for team: " + x_oblv_user_name)
        raise HTTPException(400, f"Error while attempting to calculate accuracy:" + str(excp))

    loss = get_loss(eps, delta, 1/globals.TRAIN.shape[0])
    
    score_ld = acc_ld + loss
    score_final = acc_final + loss

    return acc_ld, score_ld, acc_final, score_final, tmp_df

def get_loss(eps, delta, D, eps_sigma=100, delta_alpha=5, delta_beta=3):
  return - (eps/eps_sigma) - (1 - np.exp( - delta_alpha*delta*D))**delta_beta